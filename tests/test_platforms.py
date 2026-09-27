"""Тестове за подвижните и пропадащите платформи."""
from __future__ import annotations

import pytest

import config
from engine.input import PlayerInput
from entities.platforms import FallingPlatform, MovingPlatform
from tests.helpers import run, world_from_rows

T = config.TILE_SIZE
DT = config.FIXED_DT


def put_player_on(world, platform) -> None:
    """Слага героя върху средата на платформата и изчаква да стъпи."""
    body = world.player.body
    body.x = platform.body.center_x - body.width / 2
    body.y = platform.top - body.height - 2
    for _ in range(30):
        world.update(DT, PlayerInput())
        if body.on_ground:
            return
    raise AssertionError("героят не стъпи на платформата")


def test_player_moves_with_horizontal_platform() -> None:
    """Героят, стоящ на хоризонтална платформа, се движи заедно с нея."""
    world = world_from_rows("." * 20, "." * 20, "." * 20, "...M" + "." * 16, "." * 20,
                            "P" + "." * 18 + "X", "#" * 20)
    platform = world.platforms[0]
    assert isinstance(platform, MovingPlatform)
    put_player_on(world, platform)
    offset = world.player.body.x - platform.body.x
    run(world, config.MOVING_PLATFORM_PERIOD / 2)
    assert platform.body.x - platform.origin_x == pytest.approx(
        config.MOVING_PLATFORM_RANGE_TILES * T, abs=1.0)
    assert world.player.body.x - platform.body.x == pytest.approx(offset, abs=0.5)
    assert world.player.body.on_ground


def test_player_rides_vertical_platform_up() -> None:
    """Вертикалната платформа издига героя."""
    world = world_from_rows(*(["." * 10] * 8), "...V......", "." * 10, "P........X", "#" * 10)
    platform = world.platforms[0]
    put_player_on(world, platform)
    start_bottom = world.player.body.bottom
    run(world, config.MOVING_PLATFORM_PERIOD / 2)
    risen = start_bottom - world.player.body.bottom
    assert risen == pytest.approx(config.MOVING_PLATFORM_RANGE_TILES * T, abs=1.0)
    assert world.player.body.bottom == pytest.approx(platform.top, abs=0.5)


def test_falling_platform_drops_after_delay_and_respawns() -> None:
    """Пропадащата платформа се клатушка, пада и се връща на мястото си."""
    world = world_from_rows(*(["." * 10] * 3), "...D......", "." * 10, "." * 10,
                            "P........X", "#" * 10)
    platform = world.platforms[0]
    assert isinstance(platform, FallingPlatform)
    put_player_on(world, platform)
    run(world, config.FALLING_PLATFORM_DELAY * 0.5)
    assert platform.body.y == platform.origin_y and platform.triggered
    run(world, config.FALLING_PLATFORM_DELAY)
    assert platform.falling and platform.body.y > platform.origin_y
    run(world, config.FALLING_PLATFORM_RESPAWN)
    assert platform.body.y == platform.origin_y and not platform.triggered


def test_platform_is_one_way_from_below() -> None:
    """Под платформа се скача през нея, без удар в „таван“."""
    world = world_from_rows(*(["." * 10] * 4), "...D......", "..........", "...P.....X",
                            "#" * 10)
    run(world, 0.3)
    world.update(DT, PlayerInput(jump_pressed=True, jump_held=True))
    run(world, 0.25, PlayerInput(jump_held=True))
    assert world.player.body.bottom < world.platforms[0].top + 1


def test_platform_exposes_stand_surface_edges() -> None:
    """Платформата предоставя ръбовете, нужни на колизиите (протокол StandSurface)."""
    world = world_from_rows(*(["." * 12] * 3), "...D........", "............",
                            "P..........X", "#" * 12)
    platform = world.platforms[0]
    assert platform.left == platform.body.x and platform.right == platform.body.right
