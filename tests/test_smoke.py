"""Headless smoke тест: играта се стартира и върти кадри без грешка."""
from __future__ import annotations

import config
from engine.game import Game
from engine.states import Playing, new_session


def test_game_runs_headless_with_scripted_input() -> None:
    """Симулира 4 секунди ходене, тичане и скачане с фиксирани кадри."""
    game = Game()
    game.start(Playing(game, new_session()))
    frames = int(4 / config.FIXED_DT)
    for frame in range(frames):
        held = {"right"} if frame < frames // 2 else {"left", "run"}
        if frame % 50 < 20:
            held.add("jump")
        game.input.set_held(held)
        game.step_frame(config.FIXED_DT)
    assert game.logic_steps >= frames - 1


def test_losing_last_life_shows_game_over() -> None:
    """При последния живот смъртта води до екрана „Край на играта“."""
    from engine.states import GameOver

    game = Game()
    session = new_session()
    session.lives = 1
    playing = Playing(game, session)
    game.start(playing)
    playing.world.player.die(playing.world, "enemy")
    for _ in range(int((config.DEATH_ANIMATION_TIME + 0.2) / config.FIXED_DT)):
        game.step_frame(config.FIXED_DT)
    assert isinstance(game.states.current, GameOver)


def test_losing_a_life_restarts_level() -> None:
    """При оставащи животи нивото започва отначало с един живот по-малко."""
    game = Game()
    session = new_session()
    playing = Playing(game, session)
    game.start(playing)
    playing.world.player.die(playing.world, "enemy")
    for _ in range(int((config.DEATH_ANIMATION_TIME + 0.2) / config.FIXED_DT)):
        game.step_frame(config.FIXED_DT)
    assert game.states.current is playing
    assert session.lives == config.START_LIVES - 1
    assert not playing.world.player.is_dead
