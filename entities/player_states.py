"""Състоянията на героя (шаблон State).

Вместо много флагове (`is_jumping`, `is_hurt`, `is_dead`...) героят е винаги в
ТОЧНО едно състояние. Всяко състояние казва:
* дали героят може да се управлява (`controllable`);
* в кое състояние да се премине след стъпката (`next_state`).

Така преходите са събрани на едно място и лесно се рисува диаграма (ARCHITECTURE.md).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from entities.player import Player

#: Под тази скорост (px/s) смятаме, че героят стои.
RUN_ANIMATION_THRESHOLD = 10.0


class PlayerState:
    """Базово състояние."""

    name = "base"
    controllable = True

    def next_state(self, player: Player) -> PlayerState | None:
        """Връща новото състояние или None, ако остава същото."""
        return None


def _movement_state(player: Player) -> PlayerState:
    """Избира правилното „нормално“ състояние според движението на героя."""
    body = player.body
    if not body.on_ground:
        return JumpState() if body.vy < 0 else FallState()
    if abs(body.vx) > RUN_ANIMATION_THRESHOLD:
        return RunState()
    return IdleState()


class _MovingState(PlayerState):
    """Общо поведение за Idle/Run/Jump/Fall: преминава в правилното движение."""

    def next_state(self, player: Player) -> PlayerState | None:
        """Сменя състоянието само ако движението вече отговаря на друго."""
        wanted = _movement_state(player)
        return wanted if wanted.name != self.name else None


class IdleState(_MovingState):
    """Стои на земята."""

    name = "idle"


class RunState(_MovingState):
    """Ходи или тича по земята."""

    name = "run"


class JumpState(_MovingState):
    """Издига се във въздуха."""

    name = "jump"


class FallState(_MovingState):
    """Пада."""

    name = "fall"


class HurtState(PlayerState):
    """Кратко зашеметяване след удар – героят е отблъснат и не се управлява."""

    name = "hurt"
    controllable = False

    def next_state(self, player: Player) -> PlayerState | None:
        """След `HURT_STUN_TIME` се връща към нормалното движение."""
        if player.state_time >= config.HURT_STUN_TIME:
            return _movement_state(player)
        return None


class DeadState(PlayerState):
    """Героят е загинал – подскача и пада извън екрана. Крайно състояние."""

    name = "dead"
    controllable = False
