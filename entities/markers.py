"""Неподвижни обекти-маркери: чекпойнт (фенер) и изход (портал)."""
from __future__ import annotations

import config
from entities.entity import Entity
from level.level import Spawn

T = config.TILE_SIZE


class Checkpoint(Entity):
    """Фенер на стълб. Запален чекпойнт става новото място за възраждане.

    Хитбоксът е висок 3 тайла, за да се активира и когато героят го прескача.
    """

    kind = "checkpoint"

    def __init__(self, spawn: Spawn) -> None:
        height = config.CHECKPOINT_HEIGHT_TILES * T
        super().__init__(spawn.x, spawn.y + T - height, T, height)
        self.spawn = spawn
        self.activated = False


class ExitPortal(Entity):
    """Изходът на нивото. На ниво с бос е затворен, докато босът е жив."""

    kind = "exit"

    def __init__(self, spawn: Spawn) -> None:
        height = config.EXIT_HEIGHT_TILES * T
        inset = config.EXIT_INSET
        super().__init__(spawn.x + inset, spawn.y + T - height, T - 2 * inset, height)
        self.spawn = spawn
        self.is_open = True
