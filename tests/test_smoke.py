"""Headless smoke тест: играта се стартира и върти кадри без грешка."""
from __future__ import annotations

import config
from engine.game import Game
from engine.states import Playing


def test_game_runs_headless_with_scripted_input() -> None:
    """Симулира 4 секунди ходене, тичане и скачане с фиксирани кадри."""
    game = Game()
    game.start(Playing(game))
    frames = int(4 / config.FIXED_DT)
    for frame in range(frames):
        held = {"right"} if frame < frames // 2 else {"left", "run"}
        if frame % 50 < 20:
            held.add("jump")
        game.input.set_held(held)
        game.step_frame(config.FIXED_DT)
    assert game.logic_steps >= frames - 1
