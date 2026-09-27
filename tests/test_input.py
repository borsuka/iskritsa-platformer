"""Тестове за модула за вход."""
from __future__ import annotations

from engine.input import InputHandler


def test_press_is_consumed_once() -> None:
    """Натискането е еднократно събитие, а задържането продължава."""
    handler = InputHandler({"jump": ("space",)})
    handler.press("jump")
    snap = handler.player_snapshot()
    assert snap.jump_pressed and snap.jump_held
    snap = handler.player_snapshot()
    assert not snap.jump_pressed and snap.jump_held


def test_holding_does_not_repeat_press() -> None:
    """Повторно „натискане“ на вече задържан клавиш не е ново натискане."""
    handler = InputHandler({"jump": ("space",)})
    handler.press("jump")
    handler.end_step()
    handler.press("jump")
    assert not handler.consume("jump")


def test_direction() -> None:
    """Ляво и дясно едновременно се неутрализират."""
    handler = InputHandler({})
    handler.set_held({"left"})
    assert handler.player_snapshot().direction == -1
    handler.set_held({"left", "right"})
    assert handler.player_snapshot().direction == 0
