"""Фиксирана стъпка на времето с акумулатор.

Идеята („Fix Your Timestep“): реалното време между кадрите е различно на всеки
компютър (16 ms, 7 ms, 40 ms...). Ако местим героя с различно `dt`, физиката дава
малко различни резултати – скокът става по-висок на бавна машина. Затова
натрупваме реалното време в „акумулатор“ и изпълняваме логиката на равни порции
`FIXED_DT`. Остатъкът се пази за следващия кадър.
"""
from __future__ import annotations

import config


class FixedTimestep:
    """Брои колко логически стъпки да се изпълнят за даден кадър.

    Args:
        step: дължина на една логическа стъпка в секунди.
        max_frame_time: най-дългият кадър, който приемаме (по-дълъг се отрязва),
            за да не „замръзне“ играта в опит да навакса (spiral of death).
    """

    def __init__(self, step: float = config.FIXED_DT,
                 max_frame_time: float = config.MAX_FRAME_TIME) -> None:
        self.step = step
        self.max_frame_time = max_frame_time
        self.accumulator = 0.0

    def advance(self, frame_time: float) -> int:
        """Добавя изминалото време и връща броя стъпки, които трябва да се изпълнят."""
        self.accumulator += min(max(frame_time, 0.0), self.max_frame_time)
        steps = 0
        while self.accumulator >= self.step:
            self.accumulator -= self.step
            steps += 1
        return steps

    @property
    def alpha(self) -> float:
        """Колко от следващата стъпка е изминало (0..1) – за интерполация при рисуване."""
        return self.accumulator / self.step
