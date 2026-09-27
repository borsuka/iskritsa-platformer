"""`World` – всичко, което живее в едно заредено ниво, и логиката между тях.

Светът не рисува и не пуска звуци. Когато се случи нещо интересно (скок, монета,
удар), той записва *събитие* в `events`. Екранът `Playing` чете събитията и
пуска звук или частици. Така логиката се тества без прозорец и без звукова карта.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.input import PlayerInput
from entities.player import Player
from level.level import Level


@dataclass(frozen=True)
class GameEvent:
    """Нещо, което се е случило в света (за звук, частици и точки)."""

    kind: str
    x: float = 0.0
    y: float = 0.0


class World:
    """Състоянието на едно ниво по време на игра.

    Args:
        level: зареденото и валидирано ниво.
    """

    def __init__(self, level: Level) -> None:
        self.level = level
        start = level.player_start
        if start is None:
            raise ValueError(f"{level.file_name}: нивото няма старт 'P'")
        self.player = Player.at_spawn(start)
        self.events: list[GameEvent] = []
        self.time = 0.0

    def emit(self, kind: str, x: float = 0.0, y: float = 0.0) -> None:
        """Записва събитие за екрана (звук, частици)."""
        self.events.append(GameEvent(kind, x, y))

    def drain_events(self) -> list[GameEvent]:
        """Връща и изчиства натрупаните събития."""
        events, self.events = self.events, []
        return events

    def update(self, dt: float, inp: PlayerInput) -> None:
        """Една логическа стъпка на целия свят."""
        self.time += dt
        self.player.update_with_input(dt, inp, self)
