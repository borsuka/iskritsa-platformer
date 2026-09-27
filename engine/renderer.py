"""Рисуване на света: паралакс фон, тайлове, обекти, герой и debug слой.

Renderer-ът само ЧЕТЕ състоянието на света – никога не го променя. Затова
логиката работи и без него (в тестовете).
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

import config
from engine.assets import LAYER_WIDTH, Assets
from engine.camera import Camera
from level import tiles
from level.level import Level
from physics.body import Body

if TYPE_CHECKING:
    from engine.world import World
    from entities.enemies import Enemy
    from entities.player import Player

#: Кое състояние на героя с коя анимация се рисува.
PLAYER_ANIMATIONS = {"idle": "idle", "run": "run", "jump": "jump", "fall": "fall",
                     "hurt": "hurt", "dead": "dead"}


#: Колко кадъра в секунда има анимацията на всеки враг.
ENEMY_FRAME_RATES = {"walker": 6, "flyer": 12, "boss": 6}


#: Цветовете, през които преминава героят с Комета.
STAR_TINTS = ((90, 40, 0), (0, 60, 90), (80, 0, 80), (60, 80, 0))


def bump_lift(timer: float) -> int:
    """Колко пиксела нагоре е ударен блок (дъга от синус за BLOCK_BUMP_TIME)."""
    if timer <= 0:
        return 0
    progress = 1 - timer / config.BLOCK_BUMP_TIME
    return round(config.BLOCK_BUMP_HEIGHT * math.sin(math.pi * progress))


def blink_visible(timer: float) -> bool:
    """При неуязвимост спрайтът мига: видим е половината от времето."""
    return timer <= 0 or math.sin(timer * config.BLINK_FREQUENCY * math.pi * 2) >= 0


class Renderer:
    """Рисува света през камерата.

    Args:
        assets: кешът със спрайтове.
    """

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.debug_font = pygame.font.Font(None, 22)

    def draw(self, surface: pygame.Surface, world: World, camera: Camera,
             debug: bool = False, fps: float = 0.0) -> None:
        """Рисува целия свят."""
        offset = camera.offset
        frame = int(world.time * config.ANIMATION_FPS)
        self.draw_background(surface, world.level.meta.background, camera)
        for item in world.powerups:
            if item.emerging:   # рисува се ПРЕДИ тайловете → изглежда, че излиза от блока
                self.draw_item(surface, item.kind, item.body, offset, frame)
        self.draw_tiles(surface, world.level, offset, frame, world.block_bumps)
        self.draw_markers(surface, world, offset, frame)
        for platform in world.platforms:
            sprite = self.assets.platform(platform.kind, round(platform.body.width),
                                          world.level.meta.background)
            shake = getattr(platform, "shake_offset", 0.0)
            surface.blit(sprite, (round(platform.body.x + shake) - offset[0],
                                  round(platform.body.y) - offset[1]))
        for pickup in (*world.coins, *world.crystals):
            self.draw_item(surface, pickup.kind, pickup.body, offset, frame)
        for item in world.powerups:
            if not item.emerging:
                self.draw_item(surface, item.kind, item.body, offset, frame)
        for enemy in world.enemies:
            self.draw_enemy(surface, enemy, offset)
        self.draw_player(surface, world.player, offset)
        for projectile in (*world.enemy_projectiles, *world.fireballs):
            sprite = self.assets.item(projectile.kind, int(projectile.anim_time * 12))
            self.blit_entity(surface, sprite, (projectile.body.center_x,
                                               projectile.body.bottom + 3), offset)
        if debug:
            self.draw_debug(surface, world, camera, fps)

    # --- фон ---------------------------------------------------------------
    def draw_background(self, surface: pygame.Surface, background: str, camera: Camera) -> None:
        """Небе + три слоя, които се движат по-бавно от камерата (паралакс).

        Далечният слой се мести с 15% от скоростта на камерата, близкият с 60% –
        така мозъкът възприема дълбочина.
        """
        sky, layers = self.assets.background(background)
        surface.blit(sky, (0, 0))
        for (layer, top), factor in zip(layers, config.PARALLAX_FACTORS):
            shift = (camera.x * factor) % LAYER_WIDTH
            y = round(top - camera.y * factor * 0.5)
            x = -shift
            while x < surface.get_width():
                surface.blit(layer, (round(x), y))
                x += LAYER_WIDTH

    # --- тайлове -----------------------------------------------------------
    def draw_tiles(self, surface: pygame.Surface, level: Level, offset: tuple[int, int],
                   frame: int, bumps: dict[tuple[int, int], float] | None = None) -> None:
        """Рисува само тайловете, които попадат в екрана; ударените блокове подскачат."""
        bumps = bumps or {}
        size = config.TILE_SIZE
        off_x, off_y = offset
        first_col, first_row = max(0, off_x // size), max(0, off_y // size)
        last_col = min(level.width - 1, (off_x + surface.get_width()) // size)
        last_row = min(level.height - 1, (off_y + surface.get_height()) // size)
        background = level.meta.background
        batch: list[tuple[pygame.Surface, tuple[int, int]]] = []
        for row in range(first_row, last_row + 1):
            for col in range(first_col, last_col + 1):
                symbol = level.symbol_at(col, row)
                if symbol == tiles.EMPTY:
                    continue
                above = level.symbol_at(col, row - 1)
                top_exposed = above != symbol and not level.tile_at(col, row - 1).solid
                sprite = self.assets.tile(symbol, background, top_exposed, frame, col)
                if sprite is not None:
                    lift = bump_lift(bumps.get((col, row), 0.0))
                    batch.append((sprite, (col * size - off_x, row * size - off_y - lift)))
        surface.fblits(batch)   # един пакетен blit – много по-бързо от стотици отделни

    # --- обекти ------------------------------------------------------------
    def blit_entity(self, surface: pygame.Surface, sprite: pygame.Surface,
                    midbottom: tuple[float, float], offset: tuple[int, int]) -> None:
        """Поставя спрайт така, че долният му среден край да е на `midbottom`."""
        rect = sprite.get_rect(midbottom=(round(midbottom[0]) - offset[0],
                                          round(midbottom[1]) - offset[1]))
        surface.blit(sprite, rect)

    def draw_item(self, surface: pygame.Surface, kind: str, body: Body,
                  offset: tuple[int, int], frame: int) -> None:
        """Монета, кристал или power-up (центриран върху хитбокса)."""
        sprite = self.assets.item(kind, frame)
        rect = sprite.get_rect(center=(round(body.center_x) - offset[0],
                                       round(body.center_y) - offset[1]))
        surface.blit(sprite, rect)

    def draw_markers(self, surface: pygame.Surface, world: World, offset: tuple[int, int],
                     frame: int) -> None:
        """Изходът и чекпойнтите."""
        portal = world.exit
        sprite = self.assets.exit_portal(portal.is_open, frame)
        self.blit_entity(surface, sprite, (portal.body.center_x, portal.body.bottom), offset)
        for checkpoint in world.checkpoints:
            sprite = self.assets.checkpoint(checkpoint.activated)
            self.blit_entity(surface, sprite, (checkpoint.body.center_x, checkpoint.body.bottom),
                             offset)

    def draw_enemy(self, surface: pygame.Surface, enemy: Enemy,
                   offset: tuple[int, int]) -> None:
        """Враг с кадър според вида и поведението му."""
        frame = int(enemy.anim_time * ENEMY_FRAME_RATES.get(enemy.kind, 6))
        if enemy.kind == "hopper":
            frame = 1 if getattr(enemy, "airborne", False) else 0
        elif enemy.kind == "shooter":
            frame = 1 if getattr(enemy, "mouth_open", False) else 0
        sprite = self.assets.enemy(enemy.kind, frame, enemy.facing, getattr(enemy, "phase", 0))
        lift = 4 if enemy.kind == "flyer" else 1
        self.blit_entity(surface, sprite, (enemy.body.center_x, enemy.body.bottom + lift), offset)

    def draw_player(self, surface: pygame.Surface, player: Player,
                    offset: tuple[int, int]) -> None:
        """Героят с анимация според състоянието му; мига, докато е неуязвим."""
        if not blink_visible(player.invulnerable_timer):
            return
        body = player.body
        anim = PLAYER_ANIMATIONS.get(player.state.name, "idle")
        speed_factor = 1.0 + abs(body.vx) / config.MAX_WALK_SPEED
        frame = int(player.anim_time * config.ANIMATION_FPS * (speed_factor if anim == "run"
                                                               else 0.6))
        sprite = self.assets.player(player.form, anim, frame, player.facing)
        if player.star_timer > 0:
            sprite = sprite.copy()
            tint = STAR_TINTS[int(player.anim_time * 12) % len(STAR_TINTS)]
            sprite.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
        self.blit_entity(surface, sprite, (body.center_x, body.bottom + 1), offset)

    # --- debug -------------------------------------------------------------
    def draw_debug(self, surface: pygame.Surface, world: World, camera: Camera,
                   fps: float) -> None:
        """Хитбоксове, dead zone на камерата и текст със състоянието на героя."""
        offset = camera.offset
        for body in world.debug_bodies():
            pygame.draw.rect(surface, config.DEBUG_HITBOX, body.rect().move(-offset[0],
                                                                            -offset[1]), 1)
        zone = pygame.Rect(0, 0, config.CAMERA_DEAD_ZONE_WIDTH, config.CAMERA_DEAD_ZONE_HEIGHT)
        zone.center = (surface.get_width() // 2, surface.get_height() // 2)
        pygame.draw.rect(surface, config.DEBUG_TEXT, zone, 1)
        player = world.player
        lines = [
            f"FPS: {fps:5.1f}",
            f"pos: ({player.body.x:7.1f}, {player.body.y:7.1f})",
            f"vel: ({player.body.vx:7.1f}, {player.body.vy:7.1f})",
            f"state: {player.state.name}  form: {player.form}",
            f"on_ground: {player.body.on_ground}  one_way: {player.body.on_one_way}",
            f"coyote: {player.coyote_timer:.2f}  buffer: {player.jump_buffer_timer:.2f}",
            f"camera: ({camera.x:.0f}, {camera.y:.0f})  look-ahead: {camera.look_ahead:.0f}",
        ]
        for index, text in enumerate(lines):
            label = self.debug_font.render(text, True, config.DEBUG_TEXT)
            backdrop = pygame.Surface((label.get_width() + 6, label.get_height()),
                                      pygame.SRCALPHA)
            backdrop.fill((0, 0, 0, 150))
            surface.blit(backdrop, (6, 60 + index * 18))
            surface.blit(label, (9, 60 + index * 18))

