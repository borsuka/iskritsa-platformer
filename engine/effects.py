"""Визуални ефекти: частици, плаващи точки и анимации на победени врагове.

Ефектите са чиста „украса“ – не влияят на играта. Създават се от събитията на
света (`GameEvent`), затова логиката не знае за тях.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

import config
from engine.assets import Assets

Color = tuple[int, int, int]

SPARK_COLORS: dict[str, Color] = {
    "coin": (255, 220, 90), "crystal": (150, 230, 255), "checkpoint": (255, 200, 80),
    "hurt": (255, 90, 90), "fireball_pop": (160, 200, 255), "jump": (230, 220, 200),
    "powerup": (255, 160, 60), "level_complete": (255, 250, 200), "enemy_stomp": (220, 220, 210),
    "break": (180, 110, 70), "boss_hit": (230, 120, 255),
}


@dataclass
class Particle:
    """Малко квадратче, което лети, пада и избледнява."""

    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: Color
    size: int = 3
    gravity: bool = True


@dataclass
class FloatingText:
    """Надпис („+100“), който се издига и изчезва."""

    x: float
    y: float
    text: str
    life: float = 0.8


@dataclass
class SpriteEffect:
    """Спрайт на победен враг: смачкан (stomp) или обърнат и падащ (удар)."""

    kind: str
    facing: int
    x: float
    y: float
    vy: float
    life: float
    squashed: bool


class Effects:
    """Всички активни ефекти и тяхното обновяване/рисуване."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.sprites: list[SpriteEffect] = []
        self._rng = random.Random(7)

    def burst(self, x: float, y: float, color: Color, count: int = 8, speed: float = 160.0,
              gravity: bool = True) -> None:
        """Изстрелва частици във всички посоки."""
        for _ in range(count):
            angle = self._rng.uniform(0, math.pi * 2)
            power = self._rng.uniform(0.4, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(angle) * power,
                                           math.sin(angle) * power - speed * 0.3,
                                           config.PARTICLE_LIFETIME * self._rng.uniform(0.6, 1.0),
                                           color, self._rng.choice((2, 3, 4)), gravity))

    def on_event(self, kind: str, x: float, y: float, data: str) -> None:
        """Създава подходящ ефект за събитие от света."""
        if kind == "points":
            self.texts.append(FloatingText(x, y, f"+{data}"))
        elif kind in ("enemy_stomp", "enemy_fireball", "enemy_star"):
            enemy_kind, facing = data.split(":")
            squashed = kind == "enemy_stomp"
            self.sprites.append(SpriteEffect(enemy_kind, int(facing), x, y,
                                             0.0 if squashed else -350.0, 0.5 if squashed
                                             else 1.5, squashed))
            self.burst(x, y, SPARK_COLORS["enemy_stomp"], 6, 120)
        elif kind == "jump":
            self.burst(x, y, SPARK_COLORS["jump"], 4, 60, gravity=False)
        elif kind == "level_complete":
            self.burst(x, y, SPARK_COLORS[kind], 40, 300)
        elif kind in SPARK_COLORS:
            self.burst(x, y, SPARK_COLORS[kind], 10)

    def update(self, dt: float) -> None:
        """Движи и състарява всички ефекти."""
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            if particle.gravity:
                particle.vy += config.PARTICLE_GRAVITY * dt
            particle.life -= dt
        for text in self.texts:
            text.y -= 40 * dt
            text.life -= dt
        for sprite in self.sprites:
            if not sprite.squashed:
                sprite.vy += config.GRAVITY * dt
                sprite.y += sprite.vy * dt
            sprite.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]
        self.texts = [t for t in self.texts if t.life > 0]
        self.sprites = [s for s in self.sprites if s.life > 0]

    def draw(self, surface: pygame.Surface, offset: tuple[int, int], assets: Assets,
             font: pygame.font.Font) -> None:
        """Рисува ефектите спрямо камерата."""
        off_x, off_y = offset
        for sprite in self.sprites:
            image = assets.enemy(sprite.kind, 0, sprite.facing)
            if sprite.squashed:
                image = pygame.transform.scale(image, (image.get_width(),
                                                       max(1, image.get_height() // 3)))
            else:
                image = pygame.transform.flip(image, False, True)
            surface.blit(image, image.get_rect(center=(sprite.x - off_x, sprite.y - off_y + 6)))
        for particle in self.particles:
            alpha = max(0.0, min(1.0, particle.life / config.PARTICLE_LIFETIME))
            color = tuple(round(c * (0.4 + 0.6 * alpha)) for c in particle.color)
            pygame.draw.rect(surface, color, (round(particle.x - off_x), round(particle.y - off_y),
                                              particle.size, particle.size))
        for text in self.texts:
            label = font.render(text.text, True, config.HUD_TEXT)
            surface.blit(label, label.get_rect(center=(text.x - off_x, text.y - off_y)))
