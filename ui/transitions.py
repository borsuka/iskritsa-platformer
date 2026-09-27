"""Плавен преход (fade) между екраните: затъмняване → смяна → изсветляване."""
from __future__ import annotations

from typing import Callable

import pygame

import config

IDLE, FADING_OUT, FADING_IN = "idle", "out", "in"


class Fade:
    """Затъмнява екрана, изпълнява смяната по средата и го изсветлява.

    Args:
        duration: продължителност на всяка половина в секунди.
    """

    def __init__(self, duration: float = config.FADE_TIME) -> None:
        self.duration = duration
        self.phase = IDLE
        self.timer = 0.0
        self._on_switch: Callable[[], None] | None = None

    @property
    def active(self) -> bool:
        """Тече ли преход."""
        return self.phase != IDLE

    @property
    def blocks_input(self) -> bool:
        """Докато екранът тъмнее, логиката на стария екран е замразена."""
        return self.phase == FADING_OUT

    def start(self, on_switch: Callable[[], None]) -> None:
        """Започва преход; `on_switch` се извиква, когато екранът е напълно черен."""
        if self.phase == FADING_OUT:
            return   # вече тече преход – не започваме втори
        self.phase = FADING_OUT
        self.timer = 0.0
        self._on_switch = on_switch

    def update(self, dt: float) -> None:
        """Напредва прехода."""
        if self.phase == IDLE:
            return
        self.timer += dt
        if self.timer < self.duration:
            return
        self.timer = 0.0
        if self.phase == FADING_OUT:
            self.phase = FADING_IN
            if self._on_switch is not None:
                self._on_switch()
                self._on_switch = None
        else:
            self.phase = IDLE

    @property
    def alpha(self) -> int:
        """Прозрачност на черния слой (0 – няма, 255 – напълно черно)."""
        progress = min(1.0, self.timer / self.duration) if self.duration > 0 else 1.0
        if self.phase == FADING_OUT:
            return round(255 * progress)
        if self.phase == FADING_IN:
            return round(255 * (1 - progress))
        return 0

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува черния слой отгоре."""
        if self.alpha <= 0:
            return
        overlay = pygame.Surface(surface.get_size())
        overlay.fill(config.BLACK)
        overlay.set_alpha(self.alpha)
        surface.blit(overlay, (0, 0))
