"""Подвижни платформи: хоризонтални (`M`), вертикални (`V`) и пропадащи (`D`).

Всички платформи са „one-way“ отгоре: стъпва се върху тях, но се минава отдолу.
Всяка стъпка платформата запомня с колко се е преместила (`dx`, `dy`), а светът
премества героя, стоящ върху нея, със същото – така тя го „носи“.

Разположение: символът във файла е най-левият тайл на платформата, а горният ѝ
ръб съвпада с горния ръб на клетката.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import config
from entities.entity import Entity
from level.level import Spawn
from physics.kinematics import gravity_step

if TYPE_CHECKING:
    from engine.world import World

T = config.TILE_SIZE


class Platform(Entity):
    """Общото за подвижните платформи (реализира протокола `StandSurface`).

    Args:
        spawn: клетката от картата.
        width_tiles: ширина в тайлове.
    """

    kind = "platform"

    def __init__(self, spawn: Spawn, width_tiles: int) -> None:
        super().__init__(spawn.x, spawn.y, width_tiles * T, config.PLATFORM_THICKNESS)
        self.origin_x = spawn.x
        self.origin_y = spawn.y
        self.dx = 0.0
        self.dy = 0.0

    @property
    def left(self) -> float:
        """Левият ръб."""
        return self.body.left

    @property
    def right(self) -> float:
        """Десният ръб."""
        return self.body.right

    @property
    def top(self) -> float:
        """Горният ръб – повърхността, на която се стъпва."""
        return self.body.top

    def move_to(self, x: float, y: float) -> None:
        """Премества платформата и запомня преместването за тази стъпка."""
        self.dx, self.dy = x - self.body.x, y - self.body.y
        self.body.x, self.body.y = x, y


class MovingPlatform(Platform):
    """Платформа, която се движи напред-назад по една ос.

    Позицията следва (1 − cos(2π·t/T)) / 2 – плавно тръгване и спиране в краищата.

    Args:
        spawn: клетката от картата.
        axis: "x" (надясно от началото) или "y" (нагоре от началото).
    """

    def __init__(self, spawn: Spawn, axis: str) -> None:
        super().__init__(spawn, config.MOVING_PLATFORM_WIDTH_TILES)
        self.axis = axis
        self.kind = "platform_h" if axis == "x" else "platform_v"
        self.travel = config.MOVING_PLATFORM_RANGE_TILES * T

    def update(self, dt: float, world: World) -> None:
        """Изчислява новата позиция по времето."""
        super().update(dt, world)
        phase = 2 * math.pi * self.anim_time / config.MOVING_PLATFORM_PERIOD
        offset = self.travel * (1 - math.cos(phase)) / 2
        if self.axis == "x":
            self.move_to(self.origin_x + offset, self.origin_y)
        else:
            self.move_to(self.origin_x, self.origin_y - offset)


class FallingPlatform(Platform):
    """Платформа, която се клатушка, щом героят стъпи, после пада и се връща."""

    kind = "platform_falling"

    def __init__(self, spawn: Spawn) -> None:
        super().__init__(spawn, config.FALLING_PLATFORM_WIDTH_TILES)
        self.shake_timer = 0.0
        self.falling = False
        self.triggered = False
        self.respawn_timer = 0.0

    def trigger(self) -> None:
        """Героят е стъпил: започва клатушкането (ако още не е започнало)."""
        if not self.triggered:
            self.triggered = True
            self.shake_timer = config.FALLING_PLATFORM_DELAY

    @property
    def shake_offset(self) -> float:
        """Хоризонтално клатене за рисуване (само визуално)."""
        if self.triggered and not self.falling:
            return math.sin(self.anim_time * 60) * 2
        return 0.0

    def update(self, dt: float, world: World) -> None:
        """Клатене → падане → връщане на мястото след известно време."""
        super().update(dt, world)
        self.dx = self.dy = 0.0
        if self.triggered and not self.falling:
            self.shake_timer -= dt
            self.falling = self.shake_timer <= 0
        if not self.falling:
            return
        dy = gravity_step(self.body, dt)
        self.move_to(self.body.x, self.body.y + dy)
        self.respawn_timer += dt
        if self.respawn_timer >= config.FALLING_PLATFORM_RESPAWN:
            self.reset()

    def reset(self) -> None:
        """Връща платформата на първоначалното ѝ място."""
        self.move_to(self.origin_x, self.origin_y)
        self.dx = self.dy = 0.0
        self.body.vy = 0.0
        self.triggered = self.falling = False
        self.respawn_timer = 0.0


def create_platform(spawn: Spawn) -> Platform:
    """Фабрика: създава платформа според символа (M, V или D)."""
    if spawn.kind == "platform_h":
        return MovingPlatform(spawn, "x")
    if spawn.kind == "platform_v":
        return MovingPlatform(spawn, "y")
    return FallingPlatform(spawn)


PLATFORM_KINDS = frozenset({"platform_h", "platform_v", "platform_falling"})
