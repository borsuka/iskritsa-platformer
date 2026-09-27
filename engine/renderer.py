"""Рисуване на нивото (опростена версия от етап 2)."""
from __future__ import annotations

import pygame

import config
from level import tiles
from level.level import Level


def draw_tiles(surface: pygame.Surface, level: Level, offset_x: float = 0.0,
               offset_y: float = 0.0) -> None:
    """Рисува само видимите тайлове като цветни правоъгълници.

    Args:
        surface: къде да се рисува.
        level: нивото.
        offset_x: позиция на камерата по X (в пиксели от света).
        offset_y: позиция на камерата по Y.
    """
    palette = config.PALETTES[level.meta.background]
    size = config.TILE_SIZE
    first_col = max(0, int(offset_x // size))
    last_col = min(level.width - 1, int((offset_x + surface.get_width()) // size))
    first_row = max(0, int(offset_y // size))
    last_row = min(level.height - 1, int((offset_y + surface.get_height()) // size))
    colors = {
        tiles.SOLID: palette["ground"], tiles.ONE_WAY: palette["platform"],
        tiles.BREAKABLE: palette["brick"], tiles.SPIKES: config.WHITE,
        tiles.LAVA: (230, 90, 30), tiles.USED_BLOCK: palette["ground_dark"],
    }
    for row in range(first_row, last_row + 1):
        for col in range(first_col, last_col + 1):
            symbol = level.symbol_at(col, row)
            if symbol == tiles.EMPTY:
                continue
            color = colors.get(symbol, palette["accent"])
            rect = pygame.Rect(round(col * size - offset_x), round(row * size - offset_y),
                               size, size)
            pygame.draw.rect(surface, color, rect)
