"""Кои тайлове пресича даден правоъгълник.

Вместо да обхождаме цялата карта (хиляди тайлове), изчисляваме само колоните и
редовете, които правоъгълникът покрива. За тяло с размер под един тайл това са
най-много 2×2 = 4 клетки.
"""
from __future__ import annotations

import math
from typing import Iterator, Protocol

import config
from level.tiles import TileType


class TileGrid(Protocol):
    """Всичко, което може да отговори „какъв тайл има в клетка (col, row)“."""

    def tile_at(self, col: int, row: int) -> TileType:
        """Връща типа на тайла в клетката."""
        ...


def to_cell(coordinate: float) -> int:
    """Превръща координата в пиксели в индекс на клетка."""
    return math.floor(coordinate / config.TILE_SIZE)


def cell_span(start: float, end: float) -> range:
    """Индексите на клетките, които отсечката [start, end) пресича.

    Изваждаме малък епсилон от края, за да НЕ броим клетката, която само се
    допира до ръба (тяло, стоящо точно на земята, не „влиза“ в земята).
    """
    first = to_cell(start)
    last = to_cell(end - config.COLLISION_EPSILON)
    return range(first, max(first, last) + 1)


def tiles_in_rect(grid: TileGrid, left: float, top: float, right: float,
                  bottom: float) -> Iterator[tuple[int, int, TileType]]:
    """Обхожда клетките, които правоъгълникът пресича.

    Yields:
        (колона, ред, тип на тайла) за всяка пресечена клетка.
    """
    for row in cell_span(top, bottom):
        for col in cell_span(left, right):
            yield col, row, grid.tile_at(col, row)
