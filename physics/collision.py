"""AABB колизии с тайловата карта, разрешавани поотделно по двете оси.

Защо по оси? Ако преместим тялото едновременно по X и Y и то влезе в стена под
ъгъл, не е ясно дали да го избутаме настрани или нагоре – при грешен избор тялото
„залепва“ за ъгъла или се „качва“ по стената. Когато първо местим само по X и
разрешим колизиите по X, после само по Y и разрешим по Y, във всяка стъпка
посоката на навлизане е еднозначна и избутването винаги е в обратна посока.

Защита от тунелиране: ако за една стъпка тялото трябва да измине повече от
половин тайл, разделяме движението на няколко по-малки подстъпки. Иначе при
голяма скорост тялото може да „прескочи“ тънка стена между два кадъра.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, Sequence

import config
from physics.body import Body
from physics.tilemap_query import TileGrid, tiles_in_rect


class StandSurface(Protocol):
    """Подвижна повърхност, на която може да се стъпи отгоре (движеща се платформа)."""

    @property
    def left(self) -> float:
        """Левият ръб."""
        ...

    @property
    def right(self) -> float:
        """Десният ръб."""
        ...

    @property
    def top(self) -> float:
        """Горният ръб."""
        ...


@dataclass
class CollisionResult:
    """Какво се е случило при едно движение.

    Attributes:
        hit_left: ударило се е в стена отляво.
        hit_right: ударило се е в стена отдясно.
        hit_ceiling: ударило се е в таван.
        landed: стъпило е на нещо (земя, one-way или платформа).
        ceiling_cells: клетките на тавана, в които се е ударило (за блокове с изненада).
        platform: платформата, на която е стъпило (ако има).
    """

    hit_left: bool = False
    hit_right: bool = False
    hit_ceiling: bool = False
    landed: bool = False
    ceiling_cells: list[tuple[int, int]] = field(default_factory=list)
    platform: StandSurface | None = None

    @property
    def hit_wall(self) -> bool:
        """Ударило ли се е в стена от която и да е страна."""
        return self.hit_left or self.hit_right


def move_body(body: Body, grid: TileGrid, dx: float, dy: float,
              ignore_one_way: bool = False,
              platforms: Sequence[StandSurface] = ()) -> CollisionResult:
    """Мести тялото с (dx, dy) и го избутва извън твърдите тайлове.

    Нулира скоростта по оста, по която е имало удар. Обновява `body.on_ground`.

    Args:
        body: тялото.
        grid: картата с тайлове.
        dx: преместване по X в пиксели за тази стъпка.
        dy: преместване по Y в пиксели за тази стъпка.
        ignore_one_way: пропадане през one-way платформи (надолу + скок).
        platforms: подвижни платформи, на които може да се стъпи отгоре.
    """
    result = CollisionResult()
    substeps = max(1, math.ceil(max(abs(dx), abs(dy)) / config.MAX_SUBSTEP_DISTANCE))
    step_x, step_y = dx / substeps, dy / substeps
    body.on_one_way = False
    for _ in range(substeps):
        if step_x:
            _move_x(body, grid, step_x, result)
        _move_y(body, grid, step_y, ignore_one_way, platforms, result)
    body.on_ground = result.landed
    return result


def _move_x(body: Body, grid: TileGrid, dx: float, result: CollisionResult) -> None:
    """Движение само по X и избутване от стените. One-way платформите не пречат."""
    body.x += dx
    walls = [col for col, _row, tile in tiles_in_rect(grid, body.left, body.top,
                                                       body.right, body.bottom) if tile.solid]
    if not walls:
        return
    size = config.TILE_SIZE
    if dx > 0:
        body.x = min(walls) * size - body.width
        result.hit_right = True
    else:
        body.x = (max(walls) + 1) * size
        result.hit_left = True
    body.vx = 0.0


def _move_y(body: Body, grid: TileGrid, dy: float, ignore_one_way: bool,
            platforms: Sequence[StandSurface], result: CollisionResult) -> None:
    """Движение само по Y: приземяване (dy > 0) или удар в таван (dy < 0)."""
    previous_bottom = body.bottom
    body.y += dy
    if dy > 0:
        _resolve_landing(body, grid, previous_bottom, ignore_one_way, platforms, result)
    elif dy < 0:
        _resolve_ceiling(body, grid, result)


def _resolve_landing(body: Body, grid: TileGrid, previous_bottom: float,
                     ignore_one_way: bool, platforms: Sequence[StandSurface],
                     result: CollisionResult) -> None:
    """Намира най-високата повърхност под краката и поставя тялото върху нея."""
    size = config.TILE_SIZE
    supports: list[tuple[float, bool]] = []   # (горен ръб, твърд ли е)
    for _col, row, tile in tiles_in_rect(grid, body.left, body.top, body.right, body.bottom):
        top = row * size
        # One-way държи само ако в предишната подстъпка краката са били НАД нея.
        lands_on_one_way = (tile.one_way and not ignore_one_way
                            and previous_bottom <= top + config.COLLISION_EPSILON)
        if tile.solid or lands_on_one_way:
            supports.append((top, tile.solid))
    platform = _find_platform(body, previous_bottom, platforms)
    if platform is not None:
        supports.append((platform.top, True))
    if not supports:
        return
    best_top = min(top for top, _solid in supports)
    solid_support = any(solid for top, solid in supports if top == best_top)
    if platform is not None and platform.top == best_top:
        result.platform = platform
    body.y = best_top - body.height
    body.vy = min(body.vy, 0.0)
    body.on_one_way = not solid_support
    result.landed = True


def _find_platform(body: Body, previous_bottom: float,
                   platforms: Sequence[StandSurface]) -> StandSurface | None:
    """Платформата, върху която тялото пада в тази подстъпка (или None)."""
    found: StandSurface | None = None
    for platform in platforms:
        overlaps_x = body.left < platform.right and body.right > platform.left
        was_above = previous_bottom <= platform.top + config.COLLISION_EPSILON
        if overlaps_x and was_above and body.bottom >= platform.top:
            if found is None or platform.top < found.top:
                found = platform
    return found


def _resolve_ceiling(body: Body, grid: TileGrid, result: CollisionResult) -> None:
    """Избутва тялото под най-ниския твърд тайл над него."""
    size = config.TILE_SIZE
    hits = [(col, row) for col, row, tile in tiles_in_rect(grid, body.left, body.top,
                                                          body.right, body.bottom) if tile.solid]
    if not hits:
        return
    lowest_row = max(row for _col, row in hits)
    body.y = (lowest_row + 1) * size
    body.vy = max(body.vy, 0.0)
    result.hit_ceiling = True
    result.ceiling_cells.extend(cell for cell in hits if cell[1] == lowest_row)
