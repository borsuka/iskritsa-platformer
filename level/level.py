"""Моделът `Level`: решетка от тайлове, метаданни и точки на появяване на обекти.

`Level` не знае нищо за рисуване – той е чисти данни + заявки като
„твърд ли е тайлът на колона 5, ред 3?“. Физиката пита точно това.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import config
from level import tiles
from level.tiles import TileType


@dataclass
class LevelMeta:
    """Метаданните от секция `[meta]`."""

    name: str = "Безименно ниво"
    world: int = 1
    time_limit: int = 300
    background: str = config.DEFAULT_BACKGROUND
    music: str = "none"


@dataclass(frozen=True)
class Spawn:
    """Точка на появяване на обект, прочетена от картата.

    Attributes:
        kind: вид на обекта (напр. "walker", виж `tiles.ENTITY_SYMBOLS`).
        symbol: символът във файла.
        col: колона в картата (от 0).
        row: ред в картата (от 0).
        line: ред във файла (от 1) – за съобщения за грешка.
        column: колона във файла (от 1).
    """

    kind: str
    symbol: str
    col: int
    row: int
    line: int = 0
    column: int = 0

    @property
    def x(self) -> float:
        """Лявият ръб на клетката в пиксели."""
        return self.col * config.TILE_SIZE

    @property
    def y(self) -> float:
        """Горният ръб на клетката в пиксели."""
        return self.row * config.TILE_SIZE


@dataclass
class Level:
    """Заредено ниво.

    Attributes:
        meta: метаданни.
        grid: редове от символи на тайлове (всички редове са с еднаква дължина).
        spawns: всички обекти от картата.
        source: име на файла (за съобщения).
    """

    meta: LevelMeta
    grid: list[list[str]]
    spawns: list[Spawn] = field(default_factory=list)
    source: str = "<текст>"

    def __post_init__(self) -> None:
        self._original = [row[:] for row in self.grid]

    # --- размери -----------------------------------------------------------
    @property
    def width(self) -> int:
        """Ширина в тайлове."""
        return len(self.grid[0]) if self.grid else 0

    @property
    def height(self) -> int:
        """Височина в тайлове."""
        return len(self.grid)

    @property
    def pixel_width(self) -> int:
        """Ширина в пиксели."""
        return self.width * config.TILE_SIZE

    @property
    def pixel_height(self) -> int:
        """Височина в пиксели."""
        return self.height * config.TILE_SIZE

    @property
    def level_id(self) -> str:
        """Идентификатор на нивото – името на файла без разширение (напр. "1-2")."""
        return Path(self.source).stem

    # --- тайлове -----------------------------------------------------------
    def symbol_at(self, col: int, row: int) -> str:
        """Символът на тайла в клетка (col, row).

        Извън картата: отляво и отдясно има невидими стени, отгоре и отдолу е празно
        (отдолу е пропаст – падането там е смърт).
        """
        if col < 0 or col >= self.width:
            return tiles.SOLID
        if row < 0 or row >= self.height:
            return tiles.EMPTY
        return self.grid[row][col]

    def tile_at(self, col: int, row: int) -> TileType:
        """Типът на тайла в клетка (col, row)."""
        return tiles.tile_type(self.symbol_at(col, row))

    def is_solid(self, col: int, row: int) -> bool:
        """Твърд ли е тайлът (блокира от всички страни)."""
        return self.tile_at(col, row).solid

    def is_one_way(self, col: int, row: int) -> bool:
        """One-way платформа ли е тайлът."""
        return self.tile_at(col, row).one_way

    def set_tile(self, col: int, row: int, symbol: str) -> None:
        """Сменя тайл (напр. счупен блок → празно). Извън картата не прави нищо."""
        if 0 <= col < self.width and 0 <= row < self.height:
            self.grid[row][col] = symbol

    def reset(self) -> None:
        """Връща картата в първоначалното ѝ състояние (при рестарт на нивото)."""
        self.grid = [row[:] for row in self._original]

    # --- обекти ------------------------------------------------------------
    def spawns_of(self, kind: str) -> list[Spawn]:
        """Всички обекти от даден вид, в реда на четене (отгоре надолу, отляво надясно)."""
        return [spawn for spawn in self.spawns if spawn.kind == kind]

    @property
    def player_start(self) -> Spawn | None:
        """Стартовата позиция на героя (първото `P`)."""
        found = self.spawns_of("player")
        return found[0] if found else None

    @property
    def exit(self) -> Spawn | None:
        """Изходът (първото `X`)."""
        found = self.spawns_of("exit")
        return found[0] if found else None

    @property
    def file_name(self) -> str:
        """Името на файла без път (напр. "1-2.txt")."""
        return Path(self.source).name

    def location(self, line: int, column: int) -> str:
        """Форматира позиция във файла за съобщение за грешка."""
        return f"{self.file_name}, ред {line}, колона {column}"
