"""`World` – всичко, което живее в едно заредено ниво, и логиката между тях.

Светът не рисува и не пуска звуци. Когато се случи нещо интересно (скок, монета,
удар), той записва *събитие* в `events`. Екранът `Playing` чете събитията и
пуска звук или частици. Така логиката се тества без прозорец и без звукова карта.

Ред на една стъпка:
1. таймер на нивото;
2. героят (вход → физика);
3. враговете и снарядите;
4. взаимодействия: герой↔враг, снаряд↔герой/враг, опасности, чекпойнти, изход;
5. почистване на „мъртвите“ обекти.
"""
from __future__ import annotations

from dataclasses import dataclass

import config
from engine.input import PlayerInput
from engine.session import Session
from entities.collectibles import Coin, Crystal, PowerUp
from entities.enemies import ENEMY_CLASSES, Enemy, create_enemy
from entities.hazards import fell_into_pit, touching_hazard
from entities.markers import Checkpoint, ExitPortal
from entities.player import Player
from entities.projectiles import EnemyProjectile, Fireball
from level import tiles
from level.level import Level, Spawn
from physics.body import Body
from physics.collision import StandSurface

PLAYING, LIFE_LOST, COMPLETE = "playing", "life_lost", "complete"


@dataclass(frozen=True)
class GameEvent:
    """Нещо, което се е случило в света (за звук, частици и точки).

    Attributes:
        kind: вид на събитието (напр. "jump", "coin", "enemy_stomp").
        x: къде се е случило (X в света).
        y: къде се е случило (Y в света).
        data: допълнителна информация (напр. "walker:-1" или брой точки).
    """

    kind: str
    x: float = 0.0
    y: float = 0.0
    data: str = ""


class World:
    """Състоянието на едно ниво по време на игра.

    Args:
        level: зареденото и валидирано ниво.
        session: животи/точки/монети (ако няма – нова сесия, удобно за тестове).
        respawn: откъде да започне героят (чекпойнт); по подразбиране – от `P`.
    """

    def __init__(self, level: Level, session: Session | None = None,
                 respawn: Spawn | None = None) -> None:
        level.reset()
        self.level = level
        self.session = session if session is not None else Session()
        start = respawn or level.player_start
        if start is None or level.exit is None:
            raise ValueError(f"{level.file_name}: нивото няма старт 'P' или изход 'X'")
        self.player = Player.at_spawn(start)
        self.enemies: list[Enemy] = [create_enemy(spawn) for spawn in level.spawns
                                     if spawn.kind in ENEMY_CLASSES]
        self.enemy_projectiles: list[EnemyProjectile] = []
        self.fireballs: list[Fireball] = []
        self.platforms: list[StandSurface] = []
        self.coins = [Coin(spawn) for spawn in level.spawns_of("coin")]
        self.crystals = [Crystal(spawn, index)
                         for index, spawn in enumerate(level.spawns_of("crystal"))
                         if index not in self.session.crystals]
        self.powerups: list[PowerUp] = []
        self.block_bumps: dict[tuple[int, int], float] = {}
        self.checkpoints = [Checkpoint(spawn) for spawn in level.spawns_of("checkpoint")]
        for checkpoint in self.checkpoints:
            checkpoint.activated = respawn is not None and checkpoint.spawn == respawn
        self.exit = ExitPortal(level.exit)
        self.events: list[GameEvent] = []
        self.time = 0.0
        self.time_left = float(level.meta.time_limit)
        self.status = PLAYING
        self.active_checkpoint = respawn

    # --- събития и точки ---------------------------------------------------
    def emit(self, kind: str, x: float = 0.0, y: float = 0.0, data: str = "") -> None:
        """Записва събитие за екрана (звук, частици)."""
        self.events.append(GameEvent(kind, x, y, data))

    def drain_events(self) -> list[GameEvent]:
        """Връща и изчиства натрупаните събития."""
        events, self.events = self.events, []
        return events

    def add_points(self, points: int, x: float, y: float) -> None:
        """Добавя точки и показва плаващ надпис на мястото."""
        self.session.add_points(points)
        self.emit("points", x, y, str(points))

    def add_projectile(self, projectile: EnemyProjectile) -> None:
        """Добавя вражески снаряд."""
        self.enemy_projectiles.append(projectile)

    def debug_bodies(self) -> list[Body]:
        """Всички хитбоксове – за debug режима."""
        bodies = [self.player.body, self.exit.body]
        bodies += [entity.body for entity in (*self.enemies, *self.enemy_projectiles,
                                               *self.fireballs, *self.checkpoints, *self.coins,
                                               *self.crystals, *self.powerups)]
        return bodies

    # --- основна стъпка ----------------------------------------------------
    def update(self, dt: float, inp: PlayerInput) -> None:
        """Една логическа стъпка на целия свят."""
        if self.status != PLAYING:
            return
        self.time += dt
        self._tick_timer(dt)
        self._tick_block_bumps(dt)
        self.player.update_with_input(dt, inp, self)
        if self.player.last_collision.hit_ceiling and not self.player.is_dead:
            self._hit_block_from_below()
        for entity in (*self.enemies, *self.enemy_projectiles, *self.fireballs, *self.powerups):
            entity.update(dt, self)
        if not self.player.is_dead:
            self._collect_items()
            self._player_vs_enemies(inp)
            self._projectiles_vs_targets()
            self._check_hazards()
            self._check_checkpoints()
            self._check_exit()
        self._check_death_finished()
        self._remove_dead()

    def _tick_timer(self, dt: float) -> None:
        """Обратно броене; при 0 героят губи живот."""
        if self.player.is_dead:
            return
        self.time_left = max(0.0, self.time_left - dt)
        if self.time_left <= 0:
            self.player.die(self, "time")

    # --- взаимодействия ----------------------------------------------------
    def is_stomp(self, enemy: Enemy) -> bool:
        """Скача ли героят ВЪРХУ врага (а не се блъска в него отстрани).

        Условия: героят пада (vy > 0) и в началото на стъпката долният му ръб е
        бил в горната част на врага (над `STOMP_TOLERANCE` от височината му).
        """
        player = self.player
        threshold = enemy.body.top + enemy.body.height * config.STOMP_TOLERANCE
        return player.body.vy > 0 and player.previous_bottom <= threshold

    def _player_vs_enemies(self, inp: PlayerInput) -> None:
        """Скок отгоре побеждава врага; страничен допир наранява героя."""
        player = self.player
        for enemy in self.enemies:
            if not enemy.alive or not player.body.overlaps(enemy.body):
                continue
            if player.star_timer > 0:
                enemy.defeat(self, "star")
            elif enemy.stompable and self.is_stomp(enemy):
                enemy.defeat(self, "stomp")
                player.bounce(inp.jump_held)
            else:
                player.hurt(self, enemy.body.center_x)

    def _projectiles_vs_targets(self) -> None:
        """Вражеските снаряди нараняват героя; искровите заряди – враговете."""
        player = self.player
        for projectile in self.enemy_projectiles:
            if projectile.alive and projectile.body.overlaps(player.body):
                projectile.kill()
                player.hurt(self, projectile.body.center_x)
        for fireball in self.fireballs:
            for enemy in self.enemies:
                if fireball.alive and enemy.alive and fireball.body.overlaps(enemy.body):
                    fireball.kill()
                    self.emit("fireball_pop", fireball.body.center_x, fireball.body.center_y)
                    if enemy.fireball_vulnerable:
                        enemy.defeat(self, "fireball")

    # --- блокове -------------------------------------------------------------
    def _tick_block_bumps(self, dt: float) -> None:
        """Анимацията „подскачащ блок“ изтича."""
        self.block_bumps = {cell: timer - dt for cell, timer in self.block_bumps.items()
                            if timer - dt > 0}

    def _hit_block_from_below(self) -> None:
        """Героят удря таван: засяга се блокът, най-близо до центъра на главата."""
        size = config.TILE_SIZE
        cells = self.player.last_collision.ceiling_cells
        col, row = min(cells, key=lambda cell: abs((cell[0] + 0.5) * size
                                                    - self.player.body.center_x))
        self.bump_block(col, row)

    def bump_block(self, col: int, row: int) -> None:
        """Удар отдолу: блок с изненада пуска съдържание, чуплив блок се чупи (голям герой)."""
        symbol = self.level.symbol_at(col, row)
        tile = self.level.tile_at(col, row)
        center_x, top = (col + 0.5) * config.TILE_SIZE, row * config.TILE_SIZE
        if tile.bumpable:
            self.level.set_tile(col, row, tiles.USED_BLOCK)
            self._release_content(tiles.SURPRISE_CONTENTS[symbol], col, row)
        elif tile.breakable and self.player.is_big:
            self.level.set_tile(col, row, tiles.EMPTY)
            self.add_points(config.POINTS["brick"], center_x, top)
            self.emit("break", center_x, top + config.TILE_SIZE / 2)
            return
        self.block_bumps[(col, row)] = config.BLOCK_BUMP_TIME
        self.emit("bump", center_x, top)
        self._defeat_enemies_on_block(col, row)

    def _release_content(self, content: str, col: int, row: int) -> None:
        """Съдържанието на блок с изненада: монета веднага или power-up, който излиза."""
        if content == "coin":
            self._give_coin((col + 0.5) * config.TILE_SIZE, row * config.TILE_SIZE)
            self.emit("coin_pop", (col + 0.5) * config.TILE_SIZE, row * config.TILE_SIZE)
            return
        if content == "powerup" and self.player.is_big:
            content = "flame"   # голямата форма получава следващото ниво сила
        direction = 1 if self.player.body.center_x <= (col + 0.5) * config.TILE_SIZE else -1
        self.powerups.append(PowerUp(content, col, row, direction))
        self.emit("powerup_appear", (col + 0.5) * config.TILE_SIZE, row * config.TILE_SIZE)

    def _defeat_enemies_on_block(self, col: int, row: int) -> None:
        """Враг, стоящ върху ударения блок, отлита (класически трик)."""
        left, right, top = col * config.TILE_SIZE, (col + 1) * config.TILE_SIZE, row * config.TILE_SIZE
        for enemy in self.enemies:
            body = enemy.body
            if body.left < right and body.right > left and abs(body.bottom - top) < 2:
                enemy.defeat(self, "fireball")

    # --- предмети ------------------------------------------------------------
    def _give_coin(self, x: float, y: float) -> None:
        """Добавя монета; на всеки 100 – живот."""
        if self.session.add_coin():
            self.emit("oneup", x, y)
        self.emit("coin", x, y)

    def _collect_items(self) -> None:
        """Събиране на монети, кристали и power-up-и при допир."""
        player = self.player
        for coin in self.coins:
            if coin.body.overlaps(player.body):
                coin.kill()
                self._give_coin(coin.body.center_x, coin.body.center_y)
        for crystal in self.crystals:
            if crystal.body.overlaps(player.body):
                crystal.kill()
                self.session.crystals.add(crystal.index)
                self.add_points(config.POINTS["crystal"], crystal.body.center_x, crystal.body.top)
                self.emit("crystal", crystal.body.center_x, crystal.body.center_y)
        for item in self.powerups:
            if not item.emerging and item.body.overlaps(player.body):
                item.kill()
                if item.kind == "life":
                    self.session.lives += 1
                    self.emit("oneup", item.body.center_x, item.body.top)
                else:
                    player.collect_powerup(item.kind, self)

    def _check_hazards(self) -> None:
        """Шипове нараняват, лава и пропаст убиват моментално."""
        player = self.player
        if fell_into_pit(self.level, player.body):
            player.die(self, "pit")
            return
        hazard = touching_hazard(self.level, player.body)
        if hazard is None:
            return
        kind, source_x = hazard
        if kind == "lava":
            player.die(self, "lava")
        else:
            player.hurt(self, source_x)

    def _check_checkpoints(self) -> None:
        """Първото докосване запалва фенера и запомня точката на възраждане."""
        for checkpoint in self.checkpoints:
            if not checkpoint.activated and checkpoint.body.overlaps(self.player.body):
                checkpoint.activated = True
                self.active_checkpoint = checkpoint.spawn
                spawn = checkpoint.spawn
                self.session.checkpoint = (self.level.level_id, spawn.col, spawn.row)
                self.emit("checkpoint", checkpoint.body.center_x, checkpoint.body.top)

    def _check_exit(self) -> None:
        """Докосване на отворения изход завършва нивото."""
        if self.exit.is_open and self.exit.body.overlaps(self.player.body):
            self.status = COMPLETE
            self.emit("level_complete", self.exit.body.center_x, self.exit.body.top)

    def _check_death_finished(self) -> None:
        """След анимацията на смъртта сигнализира, че е загубен живот."""
        player = self.player
        if player.is_dead and player.state_time >= config.DEATH_ANIMATION_TIME:
            self.status = LIFE_LOST

    def _remove_dead(self) -> None:
        """Маха победените врагове и изчезналите снаряди."""
        self.enemies = [enemy for enemy in self.enemies if enemy.alive]
        self.enemy_projectiles = [shot for shot in self.enemy_projectiles if shot.alive]
        self.fireballs = [shot for shot in self.fireballs if shot.alive]
        self.coins = [coin for coin in self.coins if coin.alive]
        self.crystals = [crystal for crystal in self.crystals if crystal.alive]
        self.powerups = [item for item in self.powerups if item.alive]
