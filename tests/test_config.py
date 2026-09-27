"""Проверки на константите в config.py."""
from __future__ import annotations

import math

import config


def test_jump_velocity_is_derived_from_height() -> None:
    """Силата на скока трябва да следва от v0 = sqrt(2·g·h)."""
    expected = math.sqrt(2 * config.GRAVITY * config.JUMP_HEIGHT)
    assert math.isclose(config.JUMP_VELOCITY, expected)


def test_run_is_faster_than_walk() -> None:
    """Бягането трябва да е по-бързо от ходенето."""
    assert config.MAX_RUN_SPEED > config.MAX_WALK_SPEED


def test_every_background_has_palette() -> None:
    """Всеки свят има пълна палитра с еднакви ключове."""
    keys = set(config.PALETTES[config.DEFAULT_BACKGROUND])
    for palette in config.PALETTES.values():
        assert set(palette) == keys
