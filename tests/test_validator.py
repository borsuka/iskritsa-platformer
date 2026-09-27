"""Тестове за валидатора на нива."""
from __future__ import annotations

import pytest

from level.level import Level
from level.parser import parse_level
from level.validator import (LevelValidationError, ensure_valid, find_pit_columns,
                             validate_level)


def make(map_text: str) -> Level:
    """Парсва карта без метаданни."""
    return parse_level("[map]\n" + map_text, "t.txt")


def test_valid_level_passes() -> None:
    """Простото ниво е валидно."""
    report = validate_level(make("P...X\n#####\n"))
    assert report.ok, report.errors


def test_missing_player_is_error() -> None:
    """Липсващ 'P' е грешка."""
    report = validate_level(make("....X\n#####\n"))
    assert any("липсва старт" in error for error in report.errors)


def test_missing_exit_is_error() -> None:
    """Липсващ 'X' е грешка."""
    report = validate_level(make("P....\n#####\n"))
    assert any("липсва изход" in error for error in report.errors)


def test_duplicate_player_reports_position() -> None:
    """Втори 'P' е грешка със своя ред и колона."""
    report = validate_level(make("P.P.X\n#####\n"))
    assert any("ред 2, колона 3: втори старт" in error for error in report.errors)


def test_duplicate_exit_is_error() -> None:
    """Втори 'X' е грешка."""
    report = validate_level(make("PX..X\n#####\n"))
    assert any("втори изход" in error for error in report.errors)


def test_two_bosses_is_error() -> None:
    """Повече от един бос е грешка."""
    report = validate_level(make("P@.@X\n#####\n"))
    assert any("втори бос" in error for error in report.errors)


def test_start_over_pit_is_error() -> None:
    """Старт над пропаст би убил героя веднага."""
    report = validate_level(make("P...X\n.####\n"))
    assert any("над пропаст" in error for error in report.errors)


def test_pit_columns_are_found() -> None:
    """Колоните без опора се откриват като пропасти."""
    assert find_pit_columns(make("P...X\n##..#\n")) == [2, 3]


def test_crystal_count_is_warning_not_error() -> None:
    """Грешен брой кристали е само предупреждение."""
    report = validate_level(make("PG..X\n#####\n"))
    assert report.ok
    assert report.warnings


def test_ensure_valid_raises() -> None:
    """ensure_valid вдига изключение при грешки."""
    with pytest.raises(LevelValidationError):
        ensure_valid(make("....\n####\n"))
