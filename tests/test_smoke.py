"""Headless smoke тестове: играта се стартира и върти кадри без грешка."""
from __future__ import annotations

import config
from engine.game import Game
from engine.states import GameOver, LevelComplete, MainMenu, Pause, Playing, new_session

DT = config.FIXED_DT


def frames(game: Game, seconds: float, held: set[str] | None = None) -> None:
    """Върти `seconds` секунди с фиксирани кадри и (по желание) задържани клавиши."""
    for _ in range(round(seconds / DT)):
        if held is not None:
            game.input.set_held(held)
        game.step_frame(DT)


def playing_game(lives: int = config.START_LIVES) -> tuple[Game, Playing]:
    """Игра, стартирала директно в първото ниво."""
    game = Game(audio_enabled=False)
    session = new_session(game)
    session.lives = lives
    playing = Playing(game, session)
    game.start(playing)
    return game, playing


def test_game_runs_headless_with_scripted_input() -> None:
    """Симулира 4 секунди ходене, тичане и скачане с фиксирани кадри."""
    game, _ = playing_game()
    total = round(4 / DT)
    for frame in range(total):
        held = {"right"} if frame < total // 2 else {"left", "run"}
        if frame % 50 < 20:
            held.add("jump")
        game.input.set_held(held)
        game.step_frame(DT)
    assert game.logic_steps >= total - 1


def test_losing_last_life_shows_game_over() -> None:
    """При последния живот смъртта води до екрана „Край на играта“."""
    game, playing = playing_game(lives=1)
    playing.world.player.die(playing.world, "enemy")
    frames(game, config.DEATH_ANIMATION_TIME + config.FADE_TIME + 0.2)
    assert isinstance(game.states.current, GameOver)


def test_losing_a_life_restarts_level() -> None:
    """При оставащи животи нивото започва отначало с един живот по-малко."""
    game, playing = playing_game()
    playing.world.player.die(playing.world, "enemy")
    frames(game, config.DEATH_ANIMATION_TIME + config.FADE_TIME + 0.2)
    current = game.states.current
    assert isinstance(current, Playing) and current is not playing
    assert current.session.lives == config.START_LIVES - 1
    assert not current.world.player.is_dead


def test_pause_freezes_world_and_resumes() -> None:
    """Esc слага пауза (светът спира), второ Esc продължава."""
    game, playing = playing_game()
    game.input.press("pause")
    frames(game, DT)
    assert isinstance(game.states.current, Pause)
    time_before = playing.world.time
    frames(game, 0.5, held={"right"})
    assert playing.world.time == time_before
    game.input.set_held(set())
    game.input.press("pause")
    frames(game, DT)
    assert game.states.current is playing


def test_completing_level_saves_progress_and_unlocks_next() -> None:
    """Завършено ниво → LevelComplete, записан рекорд и отключено следващо ниво."""
    game, playing = playing_game()
    exit_body = playing.world.exit.body
    player = playing.world.player.body
    player.x, player.y = exit_body.x, exit_body.y
    frames(game, config.FADE_TIME + 0.2)
    assert isinstance(game.states.current, LevelComplete)
    assert game.progress.is_unlocked(game.level_ids[1])
    assert game.level_ids[0] in game.progress.records
    assert config.SAVE_PATH.exists()


def test_menu_navigation_starts_game() -> None:
    """От главното меню Enter стартира нова игра."""
    game = Game(audio_enabled=False)
    game.start()
    assert isinstance(game.states.current, MainMenu)
    game.input.press("confirm")
    frames(game, config.FADE_TIME + 0.1)
    assert isinstance(game.states.current, Playing)
