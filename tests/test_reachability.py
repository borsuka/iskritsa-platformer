"""Тестове за проверката на достижимост на изхода."""
from __future__ import annotations

import pytest

import config
from level.reachability import JumpProfile, ReachGrid, exit_is_reachable, simulate_jump
from level.validator import validate_level
from tests.helpers import level_from_rows


def gap_level(gap: int) -> list[str]:
    """Две площадки с пропаст между тях с ширина `gap` тайла."""
    width = 10 + gap + 10
    return ["." * width, "." * width, "." * width, "." * width,
            "P" + "." * (width - 2) + "X",
            "#" * 10 + "." * gap + "#" * 10]


@pytest.mark.parametrize("gap", [1, 3, 5])
def test_jumpable_gap_is_reachable(gap: int) -> None:
    """Пропаст, която се прескача със засилване, е проходима."""
    assert exit_is_reachable(level_from_rows(*gap_level(gap)))


def test_too_wide_gap_is_unreachable() -> None:
    """Пропаст от 9 тайла не може да се прескочи."""
    assert not exit_is_reachable(level_from_rows(*gap_level(9)))


def test_max_jump_distance_matches_physics() -> None:
    """Границата между прескочима и непрескочима пропаст следва от физиката.

    Грубо: t_полет ≈ v0/g + √(2h/(1.4g)), разстояние ≈ v_бяг · t_полет ≈ 200 px ≈ 6 тайла.
    """
    reachable = [gap for gap in range(1, 10) if exit_is_reachable(level_from_rows(*gap_level(gap)))]
    assert max(reachable) in (5, 6)


def wall_level(height: int) -> list[str]:
    """Стена с височина `height` тайла между старта и изхода."""
    rows = ["." * 20 for _ in range(8)]
    rows.append("P" + "." * 18 + "X")
    rows.append("#" * 20)
    for level in range(height):
        row = rows[8 - level]
        rows[8 - level] = row[:10] + "#" * 10
    rows[8 - height] = rows[8 - height][:19] + "X"
    rows[8] = rows[8][:19] + "#"
    return rows


def test_wall_of_three_tiles_can_be_climbed() -> None:
    """Скок от 3.5 тайла преодолява стена от 3 тайла."""
    assert exit_is_reachable(level_from_rows(*wall_level(3)))


def test_wall_of_five_tiles_blocks_exit() -> None:
    """Стена от 5 тайла е непреодолима."""
    assert not exit_is_reachable(level_from_rows(*wall_level(5)))


def test_one_way_stairs_reach_high_exit() -> None:
    """Стълба от one-way платформи води до високо място."""
    rows = [
        "............X",
        "..........###",
        "..........###",
        "......===.###",
        "..........###",
        "..........###",
        "..===.....###",
        "..........###",
        "P.........###",
        "#############",
    ]
    assert exit_is_reachable(level_from_rows(*rows))


def test_spikes_field_blocks_exit() -> None:
    """Широко поле от шипове не може да се прескочи (героят би се наранил)."""
    rows = ["." * 24] * 5 + ["P" + "." * 22 + "X", "###" + "^" * 18 + "###",
                             "#" * 24]
    assert not exit_is_reachable(level_from_rows(*rows))


def test_moving_platform_bridges_wide_gap() -> None:
    """Хоризонтална платформа прави широката пропаст проходима."""
    rows = gap_level(12)
    rows[4] = rows[4][:11] + "M" + rows[4][12:]
    assert exit_is_reachable(level_from_rows(*rows))


def test_validator_rejects_unreachable_exit() -> None:
    """Валидаторът отхвърля ниво с недостижим изход."""
    report = validate_level(level_from_rows(*wall_level(5)))
    assert any("недостижим" in error for error in report.errors)


def test_simulated_jump_lands_on_other_side() -> None:
    """Единичен симулиран скок от ръба с бягане каца отвъд пропаст от 3 тайла."""
    level = level_from_rows(*gap_level(3))
    grid = ReachGrid(level)
    profile = JumpProfile(1, config.MAX_RUN_SPEED, -config.JUMP_VELOCITY)
    landing = simulate_jump(grid, (9, 4), profile)
    assert landing is not None and landing[0] >= 13
