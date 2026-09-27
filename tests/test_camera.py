"""Тестове за камерата."""
from __future__ import annotations

import pytest

import config
from engine.camera import Camera

VIEW_W, VIEW_H = 960, 540
WORLD_W, WORLD_H = 3200, 544
DT = config.FIXED_DT


def make_camera() -> Camera:
    """Камера за ниво 100×17 тайла."""
    return Camera(VIEW_W, VIEW_H, WORLD_W, WORLD_H)


def assert_inside(camera: Camera) -> None:
    """Проверява, че изгледът е изцяло в нивото."""
    assert 0 <= camera.x <= WORLD_W - VIEW_W
    assert 0 <= camera.y <= WORLD_H - VIEW_H


@pytest.mark.parametrize("target", [(-500, -500), (0, 0), (WORLD_W + 500, WORLD_H + 500),
                                    (WORLD_W, 0), (0, WORLD_H)])
def test_camera_never_leaves_level(target: tuple[int, int]) -> None:
    """Каквато и да е целта, камерата остава в границите на нивото."""
    camera = make_camera()
    camera.snap_to(*target)
    assert_inside(camera)
    for _ in range(300):
        camera.update(target[0], target[1], 300.0, DT)
        assert_inside(camera)


def test_sweep_across_level_stays_inside() -> None:
    """Героят тича от началото до края – камерата следва, без да излиза."""
    camera = make_camera()
    camera.snap_to(0, 300)
    x = 0.0
    while x < WORLD_W:
        x += config.MAX_RUN_SPEED * DT
        camera.update(x, 300, config.MAX_RUN_SPEED, DT)
        assert_inside(camera)
    assert camera.x == pytest.approx(WORLD_W - VIEW_W, abs=1.0)


def test_dead_zone_keeps_camera_still() -> None:
    """Малко движение в центъра на екрана не мести камерата."""
    camera = make_camera()
    camera.snap_to(1600, 272)
    start_x = camera.x
    for _ in range(60):
        camera.update(1600 + 20, 272, 0.0, DT)
    assert camera.x == pytest.approx(start_x)


def test_camera_follows_with_smoothing() -> None:
    """Камерата догонва целта постепенно, а не мигновено."""
    camera = make_camera()
    camera.snap_to(1000, 272)
    start_x = camera.x
    camera.update(1400, 272, 0.0, DT)
    moved_once = camera.x - start_x
    assert 0 < moved_once < 400 - config.CAMERA_DEAD_ZONE_WIDTH / 2
    for _ in range(300):
        camera.update(1400, 272, 0.0, DT)
    focus_on_screen = 1400 - camera.x
    assert focus_on_screen <= (VIEW_W + config.CAMERA_DEAD_ZONE_WIDTH) / 2 + 0.5


def test_look_ahead_points_in_movement_direction() -> None:
    """При тичане надясно камерата гледа напред (надясно)."""
    camera = make_camera()
    for _ in range(120):
        camera.update(1600, 272, config.MAX_RUN_SPEED, DT)
    assert camera.look_ahead == pytest.approx(config.CAMERA_LOOK_AHEAD)


def test_small_level_is_centered() -> None:
    """Ниво, по-тясно от екрана, се центрира."""
    camera = Camera(VIEW_W, VIEW_H, 320, 320)
    camera.snap_to(100, 100)
    assert camera.x == pytest.approx((320 - VIEW_W) / 2)


def test_shake_fades_out() -> None:
    """Разклащането отшумява и отместването се връща към позицията."""
    camera = make_camera()
    camera.snap_to(1600, 272)
    camera.shake()
    for _ in range(60):
        camera.update(1600, 272, 0.0, DT)
    assert camera.offset == (round(camera.x), round(camera.y))
