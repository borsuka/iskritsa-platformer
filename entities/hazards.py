"""Опасности от картата: шипове (нараняват), лава (убива), пропаст (убива).

Шиповете и лавата са тайлове, но хитбоксът им е по-нисък от целия тайл – само
долната част, където реално са остриетата/повърхността. Така героят не се
наранява от „въздуха“ над тях.
"""
from __future__ import annotations

import config
from level import tiles
from level.level import Level
from physics.body import Body
from physics.tilemap_query import tiles_in_rect

HAZARD_HEIGHTS = {tiles.SPIKES: config.SPIKE_HITBOX_HEIGHT, tiles.LAVA: config.LAVA_HITBOX_HEIGHT}


def hazard_hitbox(col: int, row: int, symbol: str) -> Body:
    """Хитбоксът на опасен тайл – долните няколко пиксела от клетката."""
    size = config.TILE_SIZE
    height = HAZARD_HEIGHTS[symbol]
    return Body(col * size, (row + 1) * size - height, size, height)


def touching_hazard(level: Level, body: Body) -> tuple[str, float] | None:
    """Проверява дали тялото докосва шипове или лава.

    Returns:
        ("lava" | "spikes", център на тайла по X) или None. Лавата има предимство.
    """
    found: tuple[str, float] | None = None
    for col, row, tile in tiles_in_rect(level, body.left, body.top, body.right, body.bottom):
        if not (tile.hazard or tile.deadly):
            continue
        if not body.overlaps(hazard_hitbox(col, row, tile.symbol)):
            continue
        center_x = (col + 0.5) * config.TILE_SIZE
        if tile.deadly:
            return "lava", center_x
        found = ("spikes", center_x)
    return found


def fell_into_pit(level: Level, body: Body) -> bool:
    """Паднало ли е тялото под долния край на картата."""
    return body.top > level.pixel_height + config.PIT_DEATH_MARGIN
