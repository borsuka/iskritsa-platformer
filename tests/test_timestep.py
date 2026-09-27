"""Тестове за фиксираната стъпка на времето."""
from __future__ import annotations

import pytest

from engine.timestep import FixedTimestep

STEP = 1 / 60


def run_for(frame_time: float, total: float) -> int:
    """Симулира кадри с дадена продължителност и връща броя логически стъпки."""
    timestep = FixedTimestep(STEP, max_frame_time=1.0)
    steps = 0
    elapsed = 0.0
    while elapsed < total - 1e-9:
        steps += timestep.advance(frame_time)
        elapsed += frame_time
    return steps


@pytest.mark.parametrize("fps", [30, 60, 144, 240])
def test_same_number_of_steps_regardless_of_fps(fps: int) -> None:
    """За 2 секунди реално време логиката се обновява ~120 пъти при всеки FPS."""
    assert abs(run_for(1 / fps, 2.0) - 120) <= 1


def test_remainder_is_kept_in_accumulator() -> None:
    """Непълна стъпка не се губи, а чака следващия кадър."""
    timestep = FixedTimestep(STEP)
    assert timestep.advance(STEP * 0.6) == 0
    assert timestep.advance(STEP * 0.6) == 1
    assert 0.0 <= timestep.alpha < 1.0


def test_long_frame_is_clamped() -> None:
    """Много дълъг кадър (напр. влачене на прозореца) не води до хиляди стъпки."""
    timestep = FixedTimestep(STEP, max_frame_time=0.25)
    assert timestep.advance(10.0) == 15
