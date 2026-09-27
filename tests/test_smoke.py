"""Headless smoke тест: играта се стартира и върти кадри без грешка."""
from __future__ import annotations

import config
from engine.game import Game
from engine.states import Playing


def test_game_runs_headless_with_scripted_input() -> None:
    """Симулира 3 секунди ходене надясно и наляво с фиксирани кадри."""
    game = Game()
    game.start(Playing(game))
    frames = int(3 / config.FIXED_DT)
    for frame in range(frames):
        game.input.set_held({"right"} if frame < frames // 2 else {"left", "run"})
        game.step_frame(config.FIXED_DT)
    assert game.logic_steps >= frames - 1
