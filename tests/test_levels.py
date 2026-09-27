"""Всички нива в levels/ трябва да се зареждат, да са валидни и проходими."""
from __future__ import annotations

import pytest

import config
from level.parser import find_level_files, load_level
from level.validator import validate_level

LEVEL_FILES = find_level_files()


def test_there_are_six_levels_in_three_worlds() -> None:
    """6 нива, по 2 на свят."""
    levels = [load_level(path) for path in LEVEL_FILES]
    assert len(levels) == 6
    assert sorted(level.meta.world for level in levels) == [1, 1, 2, 2, 3, 3]


@pytest.mark.parametrize("path", LEVEL_FILES, ids=lambda path: path.stem)
def test_level_is_valid_and_exit_reachable(path) -> None:
    """Всяко ниво минава парсера и валидатора (включително reachability)."""
    report = validate_level(load_level(path))
    assert report.ok, report.errors
    assert not report.warnings, report.warnings


@pytest.mark.parametrize("path", LEVEL_FILES, ids=lambda path: path.stem)
def test_each_world_has_its_own_palette(path) -> None:
    """Светът определя фона: 1 – гора, 2 – пещера, 3 – крепост."""
    level = load_level(path)
    expected = {1: "forest", 2: "cave", 3: "castle"}[level.meta.world]
    assert level.meta.background == expected
    assert level.meta.background in config.PALETTES


def test_only_last_level_has_boss() -> None:
    """Босът е само в последното ниво."""
    bosses = [len(load_level(path).spawns_of("boss")) for path in LEVEL_FILES]
    assert bosses == [0, 0, 0, 0, 0, 1]


def test_levels_introduce_new_mechanics() -> None:
    """Всяко ниво въвежда своята нова механика (виж заданието, етап 8)."""
    def kinds(level_id: str) -> set[str]:
        return {spawn.kind for spawn in load_level(config.LEVELS_DIR / f"{level_id}.txt").spawns}

    def symbols(level_id: str) -> set[str]:
        level = load_level(config.LEVELS_DIR / f"{level_id}.txt")
        return {symbol for row in level.grid for symbol in row}

    assert "=" in symbols("1-2") and "hopper" in kinds("1-2")
    assert {"platform_h", "platform_v", "flyer"} <= kinds("2-1")
    assert "~" in symbols("2-2") and "shooter" in kinds("2-2")
    assert "platform_falling" in kinds("3-1")
    assert "boss" in kinds("3-2")
