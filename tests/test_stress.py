"""Headless стрес тест: 60 секунди случаен вход на всяко ниво без грешка.

Входът е „случаен“, но с фиксиран seed – ако тестът падне, грешката се
повтаря при всяко пускане и може да се отстрани.
"""
from __future__ import annotations

import random

import pytest

import config
from engine.game import Game
from engine.states import Playing, new_session
from level.parser import find_level_files

SIMULATED_SECONDS = 60
ACTIONS = ("left", "right", "run", "jump", "down", "shoot")
LEVEL_IDS = [path.stem for path in find_level_files()]


def random_held_keys(rng: random.Random) -> set[str]:
    """Случайна комбинация от задържани клавиши (с превес на движение надясно)."""
    held = {action for action in ACTIONS if rng.random() < 0.3}
    if rng.random() < 0.6:
        held.add("right")
        held.discard("left")
    return held


@pytest.mark.parametrize("level_id", LEVEL_IDS)
def test_sixty_seconds_of_random_input(level_id: str) -> None:
    """Играта не гърми при 60 s случаен вход; при смърт продължава от чекпойнт."""
    rng = random.Random(level_id)
    game = Game(audio_enabled=False)
    session = new_session(game, level_id)
    session.lives = 99
    game.start(Playing(game, session))
    held: set[str] = set()
    for frame in range(round(SIMULATED_SECONDS / config.FIXED_DT)):
        if frame % 15 == 0:
            held = random_held_keys(rng)
        game.input.set_held(held)
        current = game.states.current
        if isinstance(current, Playing) and frame % 240 == 0:
            current.world.player.set_form(rng.choice(("small", "big", "flame")))
        if not isinstance(current, Playing):
            game.input.press("confirm")   # напр. LevelComplete → следващото ниво
        game.step_frame(config.FIXED_DT)
    assert game.logic_steps >= round(SIMULATED_SECONDS / config.FIXED_DT) - 1
