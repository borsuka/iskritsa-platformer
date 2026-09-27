"""Физическо тяло: правоъгълник с позиция, размер и скорост (AABB)."""
from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class Body:
    """Правоъгълно тяло, подравнено по осите (Axis-Aligned Bounding Box).

    Позицията е горният ляв ъгъл в пиксели, като float – така бавното движение
    (напр. 0.3 px на стъпка) не се губи от закръгляне.

    Attributes:
        x: лявият ръб.
        y: горният ръб (оста Y сочи надолу, както на екрана).
        width: ширина.
        height: височина.
        vx: хоризонтална скорост в px/s (положителна = надясно).
        vy: вертикална скорост в px/s (положителна = надолу).
        on_ground: стои ли тялото на нещо след последното движение.
        on_one_way: стои ли САМО на one-way платформа (може да пропадне през нея).
    """

    x: float
    y: float
    width: float
    height: float
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    on_one_way: bool = False

    @property
    def left(self) -> float:
        """Левият ръб."""
        return self.x

    @property
    def right(self) -> float:
        """Десният ръб."""
        return self.x + self.width

    @property
    def top(self) -> float:
        """Горният ръб."""
        return self.y

    @property
    def bottom(self) -> float:
        """Долният ръб."""
        return self.y + self.height

    @property
    def center_x(self) -> float:
        """Центърът по X."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Центърът по Y."""
        return self.y + self.height / 2

    def overlaps(self, other: Body) -> bool:
        """Застъпват ли се двата правоъгълника (допирът по ръб не се брои)."""
        return (self.left < other.right and self.right > other.left
                and self.top < other.bottom and self.bottom > other.top)

    def rect(self) -> pygame.Rect:
        """Цял правоъгълник за рисуване (закръглена позиция)."""
        return pygame.Rect(round(self.x), round(self.y), round(self.width), round(self.height))

    def resize_keep_feet(self, width: float, height: float) -> None:
        """Сменя размера, като запазва долния ръб и центъра по X (краката остават на земята)."""
        center_x, bottom = self.center_x, self.bottom
        self.width, self.height = width, height
        self.x = center_x - width / 2
        self.y = bottom - height
