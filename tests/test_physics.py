"""Тестове за физиката: гравитация, скок, ускорение."""
from __future__ import annotations

import math

import pytest

import config
from engine.input import PlayerInput
from physics.body import Body
from physics.kinematics import approach, gravity_step
from tests.helpers import run, settle, world_from_rows

FLAT = ("." * 40, "." * 40, "." * 40, "." * 40, "." * 40, "P" + "." * 38 + "X", "#" * 40)


def test_approach_does_not_overshoot() -> None:
    """approach спира точно в целта."""
    assert approach(0, 10, 3) == 3
    assert approach(9, 10, 3) == 10
    assert approach(10, 0, 4) == 6


def test_gravity_step_matches_formula() -> None:
    """За 1 s свободно падане тялото изминава g·t²/2 (без ограничение на скоростта)."""
    body = Body(0, 0, 10, 10)
    total = 0.0
    for _ in range(60):
        total += gravity_step(body, 1 / 60, gravity=1000, max_fall=10_000)
    assert math.isclose(total, 1000 / 2, rel_tol=1e-9)


def test_fall_speed_is_capped() -> None:
    """Скоростта на падане не надвишава MAX_FALL_SPEED."""
    body = Body(0, 0, 10, 10)
    for _ in range(300):
        gravity_step(body, 1 / 60)
    assert body.vy == config.MAX_FALL_SPEED


def test_body_falls_and_stops_on_ground() -> None:
    """Героят пада от въздуха и застава на земята."""
    world = world_from_rows("P..X", "....", "....", "....", "####")
    settle(world)
    body = world.player.body
    assert body.on_ground
    assert body.bottom == 4 * config.TILE_SIZE
    assert body.vy == 0


def measure_jump_height(inp_factory) -> float:
    """Връща максималната височина на скок в пиксели от земята."""
    world = world_from_rows(*FLAT)
    settle(world)
    ground = world.player.body.bottom
    highest = ground
    for step in range(90):
        world.update(config.FIXED_DT, inp_factory(step))
        highest = min(highest, world.player.body.bottom)
    return ground - highest


def test_full_jump_height_matches_config() -> None:
    """Задържан скок достига JUMP_HEIGHT с точност ±5%."""
    height = measure_jump_height(lambda step: PlayerInput(jump_pressed=step == 0,
                                                          jump_held=True))
    assert height == pytest.approx(config.JUMP_HEIGHT, rel=0.05)


def test_released_jump_is_lower() -> None:
    """Кратко натиснат скок е значително по-нисък (променлива височина)."""
    full = measure_jump_height(lambda step: PlayerInput(jump_pressed=step == 0,
                                                        jump_held=True))
    short = measure_jump_height(lambda step: PlayerInput(jump_pressed=step == 0,
                                                         jump_held=step < 4))
    assert short < full * 0.6


def test_walk_reaches_max_speed_and_stops_with_friction() -> None:
    """Ускорение до максималната скорост и спиране от триенето."""
    world = world_from_rows(*FLAT)
    settle(world)
    run(world, 0.5, PlayerInput(right=True))
    assert world.player.body.vx == pytest.approx(config.MAX_WALK_SPEED)
    run(world, 0.5)
    assert world.player.body.vx == 0


def test_run_is_faster_than_walk_in_game() -> None:
    """С Shift героят тича по-бързо."""
    world = world_from_rows(*FLAT)
    settle(world)
    run(world, 0.5, PlayerInput(right=True, run=True))
    assert world.player.body.vx == pytest.approx(config.MAX_RUN_SPEED)


def test_same_result_regardless_of_frame_rate() -> None:
    """Fixed timestep: две симулации с един и същ вход дават идентичен резултат."""
    results = []
    for _ in range(2):
        world = world_from_rows(*FLAT)
        run(world, 1.5, lambda step: PlayerInput(right=True, jump_pressed=step == 40,
                                                 jump_held=step < 60))
        results.append((world.player.body.x, world.player.body.y))
    assert results[0] == results[1]
