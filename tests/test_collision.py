"""Тестове за колизиите с тайловата карта."""
from __future__ import annotations

import config
from physics.body import Body
from physics.collision import move_body
from physics.tilemap_query import cell_span, tiles_in_rect
from tests.helpers import level_from_rows

T = config.TILE_SIZE


def test_cell_span_excludes_touching_edge() -> None:
    """Тяло, което само се допира до ръба на клетка, не я „пресича“."""
    assert list(cell_span(0, T)) == [0]
    assert list(cell_span(10, T + 1)) == [0, 1]


def test_tiles_in_rect_only_near_body() -> None:
    """Проверяват се само клетките около тялото, не цялата карта."""
    level = level_from_rows("P........X", "##########")
    cells = list(tiles_in_rect(level, 0, 0, 20, 20))
    assert len(cells) == 1


def test_body_lands_on_floor() -> None:
    """Падащо тяло спира точно върху земята."""
    level = level_from_rows("P..X", "....", "####")
    body = Body(4, 0, 20, 20, vy=300)
    result = move_body(body, level, 0, 60)
    assert result.landed and body.on_ground
    assert body.bottom == 2 * T
    assert body.vy == 0


def test_wall_stops_horizontal_movement() -> None:
    """Стена спира движението по X и нулира скоростта."""
    level = level_from_rows("P.#X", "####")
    body = Body(0, 10, 20, 20, vx=100)
    result = move_body(body, level, 50, 0)
    assert result.hit_right
    assert body.right == 2 * T
    assert body.vx == 0


def test_no_tunneling_through_thin_wall_at_high_speed() -> None:
    """При огромна скорост тялото пак не минава през стена с дебелина 1 тайл."""
    level = level_from_rows("P...#....X", "##########")
    body = Body(0, T - 20, 20, 20)
    move_body(body, level, 600, 0)
    assert body.right <= 4 * T


def test_no_tunneling_through_thin_floor() -> None:
    """Много бързо падане не пробива тънка one-way платформа."""
    level = level_from_rows("P..X", "....", "....", "====", "....", "....")
    body = Body(4, 0, 20, 20)
    result = move_body(body, level, 0, 150)
    assert result.landed
    assert body.bottom == 3 * T


def test_one_way_lets_body_pass_from_below() -> None:
    """Отдолу нагоре през one-way платформа се минава свободно."""
    level = level_from_rows("P..X", "....", "====", "....", "####")
    body = Body(4, 3 * T + 5, 20, 20, vy=-500)
    result = move_body(body, level, 0, -3 * T)
    assert not result.hit_ceiling
    assert body.top < 2 * T


def test_one_way_holds_from_above() -> None:
    """Отгоре one-way платформата държи."""
    level = level_from_rows("P..X", "....", "====", "....", "####")
    body = Body(4, T - 20, 20, 20, vy=200)
    move_body(body, level, 0, 40)
    assert body.bottom == 2 * T and body.on_ground and body.on_one_way


def test_one_way_ignored_when_dropping() -> None:
    """При пропадане (надолу + скок) one-way платформата се пренебрегва."""
    level = level_from_rows("P..X", "....", "====", "....", "####")
    body = Body(4, 2 * T - 20, 20, 20, vy=200)
    move_body(body, level, 0, 10, ignore_one_way=True)
    assert not body.on_ground


def test_body_already_inside_one_way_is_not_snapped_up() -> None:
    """Тяло, което е било под ръба на платформата, не бива „изстреляно“ нагоре върху нея."""
    level = level_from_rows("P..X", "....", "====", "....", "####")
    body = Body(4, 2 * T - 10, 20, 20, vy=100)
    move_body(body, level, 0, 5)
    assert not body.on_ground


def test_ceiling_is_reported_with_cells() -> None:
    """Удар в таван връща клетката на тавана (за блоковете с изненада)."""
    level = level_from_rows("..?.", "P..X", "####")
    body = Body(2 * T + 4, T + 2, 20, 20, vy=-400)
    result = move_body(body, level, 0, -20)
    assert result.hit_ceiling
    assert (2, 0) in result.ceiling_cells
    assert body.top == T


def test_sliding_along_wall_does_not_stick() -> None:
    """Скок до стена: тялото се плъзга по нея, а не залепва за ъгъла."""
    level = level_from_rows("....#", "....#", "P...#", "#####")
    body = Body(4 * T - 25, T, 20, 20)   # десният ръб е на 5 px от стената
    result = move_body(body, level, 20, -10)
    assert result.hit_right and not result.hit_ceiling
    assert body.top == T - 10
