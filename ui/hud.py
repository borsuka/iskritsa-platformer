"""HUD – информационната лента по време на игра.

Показва: животи, монети, кристали в нивото, свят-ниво, точки, оставащо време,
таймер на Кометата и HP лентата на боса.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import config
from engine.assets import Assets

if TYPE_CHECKING:
    from engine.session import Session
    from engine.world import World

MARGIN = 12
ICON_SIZE = 22
LOW_TIME_WARNING = 30   # s, под това времето става червено


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str,
              position: tuple[int, int], color: tuple[int, int, int] = config.HUD_TEXT,
              anchor: str = "topleft") -> pygame.Rect:
    """Рисува текст със сянка (по-четлив върху всякакъв фон).

    Args:
        surface: къде.
        font: шрифт.
        text: текстът.
        position: точката на закрепване.
        color: цвят.
        anchor: коя точка на правоъгълника е `position` (topleft, center, topright...).
    """
    label = font.render(text, True, color)
    shadow = font.render(text, True, config.HUD_SHADOW)
    rect = label.get_rect(**{anchor: position})
    surface.blit(shadow, rect.move(2, 2))
    surface.blit(label, rect)
    return rect


class Hud:
    """Рисува HUD-а.

    Args:
        assets: за иконите (фенерче, монета, кристал).
    """

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.font = pygame.font.Font(None, 30)
        self.small_font = pygame.font.Font(None, 22)

    def draw(self, surface: pygame.Surface, world: World, session: Session) -> None:
        """Рисува цялата лента."""
        backdrop = pygame.Surface((config.SCREEN_WIDTH, 44), pygame.SRCALPHA)
        backdrop.fill((0, 0, 0, 90))
        surface.blit(backdrop, (0, 0))
        self._draw_left(surface, world, session)
        self._draw_center(surface, world)
        self._draw_right(surface, world, session)
        if world.boss is not None and world.boss.active:
            self._draw_boss_bar(surface, world)

    def _draw_left(self, surface: pygame.Surface, world: World, session: Session) -> None:
        """Животи, монети и кристалите на нивото."""
        x = MARGIN
        surface.blit(self.assets.lantern_icon(ICON_SIZE), (x, 10))
        x = draw_text(surface, self.font, f"× {session.lives}", (x + ICON_SIZE + 4, 12)).right
        coin = pygame.transform.smoothscale(self.assets.item("coin", 0), (16, 16))
        surface.blit(coin, (x + 18, 13))
        x = draw_text(surface, self.font, f"× {session.coins:02d}", (x + 38, 12)).right
        crystal = pygame.transform.smoothscale(self.assets.item("crystal", 0), (14, 18))
        dim = crystal.copy()
        dim.set_alpha(60)
        total = len(world.level.spawns_of("crystal"))
        for index in range(total):
            icon = crystal if index in session.crystals else dim
            surface.blit(icon, (x + 20 + index * 17, 12))

    def _draw_center(self, surface: pygame.Surface, world: World) -> None:
        """Свят-ниво и името на нивото."""
        center = config.SCREEN_WIDTH // 2
        level = world.level
        draw_text(surface, self.font, f"СВЯТ {level.level_id}", (center, 6), config.HUD_ACCENT,
                  "midtop")
        draw_text(surface, self.small_font, level.meta.name, (center, 28), anchor="midtop")

    def _draw_right(self, surface: pygame.Surface, world: World, session: Session) -> None:
        """Точки, време и таймер на Кометата."""
        right = config.SCREEN_WIDTH - MARGIN
        seconds = int(world.time_left)
        time_color = config.BOSS_BAR_FG if seconds < LOW_TIME_WARNING else config.HUD_TEXT
        rect = draw_text(surface, self.font, f"ВРЕМЕ {seconds:3d}", (right, 12), time_color,
                         "topright")
        rect = draw_text(surface, self.font, f"ТОЧКИ {session.score:06d}",
                         (rect.left - 24, 12), anchor="topright")
        star = world.player.star_timer
        if star > 0:
            draw_text(surface, self.small_font, f"Комета {star:0.1f}s", (right, 48),
                      config.HUD_ACCENT, "topright")

    def _draw_boss_bar(self, surface: pygame.Surface, world: World) -> None:
        """HP лентата на боса."""
        boss = world.boss
        assert boss is not None
        width, height = 300, 14
        rect = pygame.Rect(0, 0, width, height)
        rect.midtop = (config.SCREEN_WIDTH // 2, 56)
        pygame.draw.rect(surface, config.BOSS_BAR_BG, rect.inflate(6, 6), border_radius=4)
        filled = rect.copy()
        filled.width = round(width * max(0, boss.hp) / config.BOSS_MAX_HP)
        pygame.draw.rect(surface, config.BOSS_BAR_FG, filled, border_radius=3)
        draw_text(surface, self.small_font, "Сенкоглав", (rect.centerx, rect.bottom + 6),
                  anchor="midtop")
