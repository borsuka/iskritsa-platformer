"""Базов клас за всичко, което живее в нивото и се движи или взаимодейства."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import config
from physics.body import Body

if TYPE_CHECKING:
    from engine.world import World


class Entity:
    """Обект в света: има тяло (хитбокс), посока и таймер за анимация.

    Args:
        x: лявият ръб в пиксели.
        y: горният ръб в пиксели.
        width: ширина на хитбокса.
        height: височина на хитбокса.
    """

    #: Вид на обекта – използва се за точки, рисуване и дебъг.
    kind = "entity"

    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        self.body = Body(x, y, width, height)
        self.alive = True
        self.facing = 1
        self.anim_time = 0.0

    @classmethod
    def feet_in_cell(cls, col: int, row: int, width: float, height: float) -> tuple[float, float]:
        """Позиция (x, y), при която обект с даден размер стои на дъното на клетката."""
        size = config.TILE_SIZE
        return col * size + (size - width) / 2, (row + 1) * size - height

    @property
    def rect(self) -> pygame.Rect:
        """Хитбоксът като pygame.Rect (за рисуване и дебъг)."""
        return self.body.rect()

    def update(self, dt: float, world: World) -> None:
        """Обновява обекта с една логическа стъпка."""
        self.anim_time += dt

    def kill(self) -> None:
        """Маха обекта от света в края на стъпката."""
        self.alive = False
