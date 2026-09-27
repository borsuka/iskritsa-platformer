"""Малки формули за движение, използвани от героя, враговете и предметите."""
from __future__ import annotations

import config
from physics.body import Body


def approach(current: float, target: float, max_delta: float) -> float:
    """Приближава `current` към `target` с най-много `max_delta`, без да го подминава.

    Така се реализират ускорението и триенето: скоростта „пълзи“ към целта с
    постоянна стъпка `ускорение · dt`.
    """
    if current < target:
        return min(current + max_delta, target)
    return max(current - max_delta, target)


def gravity_step(body: Body, dt: float, gravity: float = config.GRAVITY,
                 max_fall: float = config.MAX_FALL_SPEED,
                 fall_multiplier: float = 1.0) -> float:
    """Прилага гравитацията върху `body.vy` и връща вертикалното преместване.

    Използваме средната скорост за стъпката (метод на трапеца):
        dy = (v_старо + v_ново) / 2 · dt
    За постоянно ускорение това е ТОЧНО решение на уравнението y = v0·t + g·t²/2,
    затова височината на скока съвпада с формулата v0 = √(2·g·h) независимо от dt.

    Args:
        body: тялото (скоростта му се променя).
        dt: стъпка по време.
        gravity: ускорение надолу.
        max_fall: крайна скорост на падане.
        fall_multiplier: множител на гравитацията, докато тялото пада (vy > 0).
    """
    effective = gravity * (fall_multiplier if body.vy > 0 else 1.0)
    old_vy = body.vy
    body.vy = min(body.vy + effective * dt, max_fall)
    return (old_vy + body.vy) / 2 * dt
