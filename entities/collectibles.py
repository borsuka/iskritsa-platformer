"""Предмети за събиране: искри (монети), слънчеви кристали и power-up-и.

Power-up-ите в играта (всички оригинални):
* **Жарава** (`powerup`) – малката Искрица става голяма;
* **Пламък** (`flame`) – голяма форма, която изстрелва искрови заряди;
* **Комета** (`comet`) – 8 s неуязвимост, враговете падат при допир;
* **Фенерче** (`life`) – допълнителен живот.

Power-up-ите излизат бавно от блока, в който са били скрити, и след това се
движат по свой начин (плъзгат се, стоят или подскачат).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import config
from entities.entity import Entity
from level.level import Spawn
from physics.collision import move_body
from physics.kinematics import gravity_step

if TYPE_CHECKING:
    from engine.world import World

T = config.TILE_SIZE
COIN_SIZE = 16
CRYSTAL_SIZE = (22, 28)
POWERUP_SIZE = 24


class Coin(Entity):
    """Искра – неподвижна монета от картата."""

    kind = "coin"

    def __init__(self, spawn: Spawn) -> None:
        offset = (T - COIN_SIZE) / 2
        super().__init__(spawn.x + offset, spawn.y + offset, COIN_SIZE, COIN_SIZE)


class Crystal(Entity):
    """Голям слънчев кристал. `index` е поредният му номер в нивото (за 100%)."""

    kind = "crystal"

    def __init__(self, spawn: Spawn, index: int) -> None:
        width, height = CRYSTAL_SIZE
        super().__init__(spawn.x + (T - width) / 2, spawn.y + T - height, width, height)
        self.index = index


class PowerUp(Entity):
    """Power-up, излизащ от блок.

    Args:
        kind: "powerup" (Жарава), "flame", "comet" или "life".
        col: колона на блока, от който излиза.
        row: ред на блока.
        direction: накъде да тръгне след излизането (1 надясно, -1 наляво).
    """

    def __init__(self, kind: str, col: int, row: int, direction: int = 1) -> None:
        offset = (T - POWERUP_SIZE) / 2
        super().__init__(col * T + offset, row * T + (T - POWERUP_SIZE), POWERUP_SIZE,
                         POWERUP_SIZE)
        self.kind = kind
        self.facing = direction
        self.emerge_target = row * T - POWERUP_SIZE   # горният ръб на блока минус височината
        self.emerging = True

    @property
    def moves(self) -> bool:
        """Дали предметът се плъзга (Пламъкът стои на място)."""
        return self.kind != "flame"

    def update(self, dt: float, world: World) -> None:
        """Излизане от блока, после движение с гравитация и колизии."""
        super().update(dt, world)
        body = self.body
        if self.emerging:
            body.y -= config.POWERUP_EMERGE_SPEED * dt
            if body.y <= self.emerge_target:
                body.y = self.emerge_target
                self.emerging = False
            return
        body.vx = self.facing * config.POWERUP_SPEED if self.moves else 0.0
        result = move_body(body, world.level, body.vx * dt, gravity_step(body, dt),
                           platforms=world.platforms)
        if result.hit_wall:
            self.facing = -self.facing
        if result.landed and self.kind == "comet":
            body.vy = -config.COMET_BOUNCE_VELOCITY
        if body.top > world.level.pixel_height + config.PIT_DEATH_MARGIN:
            self.kill()
