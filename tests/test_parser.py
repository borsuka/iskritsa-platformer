"""Тестове за парсера на нива."""
from __future__ import annotations

import pytest

from level import tiles
from level.parser import LevelFormatError, parse_level

SIMPLE = """\
# коментар
[meta]
name = Тестово ниво
world = 2
time_limit = 120
background = cave

[map]
..C..
P...X
#####
"""


def test_meta_is_parsed() -> None:
    """Всички ключове от [meta] се четат с правилния тип."""
    level = parse_level(SIMPLE, "test.txt")
    assert level.meta.name == "Тестово ниво"
    assert level.meta.world == 2
    assert level.meta.time_limit == 120
    assert level.meta.background == "cave"


def test_map_dimensions_and_tiles() -> None:
    """Картата има правилни размери, а обектите оставят празни клетки."""
    level = parse_level(SIMPLE, "test.txt")
    assert (level.width, level.height) == (5, 3)
    assert level.symbol_at(0, 2) == tiles.SOLID
    assert level.symbol_at(0, 1) == tiles.EMPTY  # на мястото на P
    assert level.is_solid(4, 2)


def test_spawns_are_collected_with_positions() -> None:
    """Обектите се записват с колона/ред в картата и ред/колона във файла."""
    level = parse_level(SIMPLE, "test.txt")
    assert level.player_start is not None
    assert (level.player_start.col, level.player_start.row) == (0, 1)
    assert (level.player_start.line, level.player_start.column) == (10, 1)
    coin = level.spawns_of("coin")[0]
    assert (coin.col, coin.row) == (2, 0)


def test_short_rows_are_padded() -> None:
    """Редове с различна дължина се допълват с '.'."""
    level = parse_level("[map]\nP\n...X\n####\n", "pad.txt")
    assert level.width == 4
    assert level.symbol_at(3, 0) == tiles.EMPTY


def test_blank_edge_lines_are_ignored() -> None:
    """Празни редове в началото и края на картата не стават редове."""
    level = parse_level("[map]\n\n\nP.X\n###\n\n\n", "blank.txt")
    assert level.height == 2


def test_blank_line_inside_map_is_empty_row() -> None:
    """Празен ред в средата на картата е ред от празни клетки."""
    level = parse_level("[map]\nP.X\n\n###\n", "mid.txt")
    assert level.height == 3
    assert level.symbol_at(1, 1) == tiles.EMPTY


def test_map_comment_needs_space() -> None:
    """В [map] коментар е само '# ', защото '#' е земя."""
    level = parse_level("[map]\n# коментар\nP.X\n###\n", "c.txt")
    assert level.height == 2
    assert level.is_solid(0, 1)


def test_unknown_symbol_reports_line_and_column() -> None:
    """Непознат символ дава грешка с ред и колона."""
    text = "[meta]\nname = x\n[map]\nP...\n..Z.\n####\n"
    with pytest.raises(LevelFormatError) as info:
        parse_level(text, "levels/1-2.txt")
    error = info.value
    assert (error.line, error.column) == (5, 3)
    assert str(error) == "1-2.txt, ред 5, колона 3: непознат символ 'Z'"


@pytest.mark.parametrize("text, line", [
    ("[meta]\nworld = едно\n[map]\nP.X\n###\n", 2),
    ("[meta]\ntime_limit = -5\n[map]\nP.X\n###\n", 2),
    ("[meta]\nspeed = 3\n[map]\nP.X\n###\n", 2),
    ("[meta]\nбез равно\n[map]\nP.X\n###\n", 2),
    ("[meta]\nbackground = космос\n[map]\nP.X\n###\n", 2),
    ("[meta]\nname = a\nname = b\n[map]\nP.X\n###\n", 3),
    ("[meta]\n[secret]\n[map]\nP.X\n###\n", 2),
    ("name = x\n[map]\nP.X\n###\n", 1),
    ("[map]\nP.X\n[map]\n###\n", 3),
])
def test_format_errors_have_line_numbers(text: str, line: int) -> None:
    """Грешките във формата посочват точния ред."""
    with pytest.raises(LevelFormatError) as info:
        parse_level(text, "bad.txt")
    assert info.value.line == line


def test_missing_map_section() -> None:
    """Файл без [map] е грешка."""
    with pytest.raises(LevelFormatError, match="липсва секция"):
        parse_level("[meta]\nname = x\n", "nomap.txt")


def test_empty_map_section() -> None:
    """Празна [map] е грешка."""
    with pytest.raises(LevelFormatError, match="празна"):
        parse_level("[map]\n\n\n", "empty.txt")


def test_missing_file_is_format_error(tmp_path) -> None:
    """Липсващ файл дава LevelFormatError, а не срив."""
    from level.parser import load_level

    with pytest.raises(LevelFormatError):
        load_level(tmp_path / "няма.txt")


def test_level_id_from_file_name() -> None:
    """Идентификаторът на нивото е името на файла без разширение."""
    level = parse_level("[map]\nP.X\n###\n", "levels/2-1.txt")
    assert level.level_id == "2-1"


def test_reset_restores_tiles() -> None:
    """reset() връща счупените блокове."""
    level = parse_level("[map]\nPBX\n###\n", "r.txt")
    level.set_tile(1, 0, tiles.EMPTY)
    level.reset()
    assert level.symbol_at(1, 0) == tiles.BREAKABLE


def test_outside_map_has_walls_and_pit() -> None:
    """Отстрани има невидими стени, а отдолу – пропаст."""
    level = parse_level("[map]\nP.X\n###\n", "o.txt")
    assert level.is_solid(-1, 0) and level.is_solid(level.width, 0)
    assert not level.is_solid(0, level.height)
