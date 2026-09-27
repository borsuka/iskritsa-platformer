"""Помощни функции за тестовете: бързо създаване на нива и симулация."""
from __future__ import annotations

from typing import Callable

import config
from engine.input import PlayerInput
from engine.world import World
from level.level import Level
from level.parser import parse_level

NO_INPUT = PlayerInput()


def level_from_rows(*rows: str, name: str = "test.txt") -> Level:
    """Създава ниво от редове на карта."""
    return parse_level("[map]\n" + "\n".join(rows) + "\n", name)


def world_from_rows(*rows: str) -> World:
    """Създава свят от редове на карта."""
    return World(level_from_rows(*rows))


def run(world: World, seconds: float,
        inp: PlayerInput | Callable[[int], PlayerInput] = NO_INPUT) -> None:
    """Върти света `seconds` секунди с фиксирана стъпка.

    Args:
        world: светът.
        seconds: колко секунди да се симулират.
        inp: постоянен вход или функция „номер на стъпка → вход“.
    """
    steps = round(seconds / config.FIXED_DT)
    for step in range(steps):
        current = inp(step) if callable(inp) else inp
        world.update(config.FIXED_DT, current)


def settle(world: World) -> None:
    """Оставя героя да падне и да застане на земята."""
    run(world, 0.5)
