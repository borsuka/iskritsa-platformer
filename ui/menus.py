"""Прости менюта с клавиатурна навигация и общ декоративен фон."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame

import config
from engine.assets import Assets, vertical_gradient
from engine.input import InputHandler
from ui.hud import draw_text


@dataclass
class MenuItem:
    """Един ред от меню.

    Attributes:
        label: текстът.
        action: какво да се изпълни при избор.
        enabled: може ли да се избере (напр. заключено ниво).
        detail: допълнителен текст вдясно (рекорд, „заключено“...).
    """

    label: str
    action: Callable[[], None]
    enabled: bool = True
    detail: str = ""


class Menu:
    """Вертикален списък с избираеми редове.

    Args:
        items: редовете.
    """

    def __init__(self, items: list[MenuItem]) -> None:
        self.items = items
        self.selected = next((index for index, item in enumerate(items) if item.enabled), 0)

    def move(self, step: int) -> bool:
        """Мести избора с `step`, прескачайки неактивните. Връща дали е помръднал."""
        count = len(self.items)
        index = self.selected
        for _ in range(count):
            index = (index + step) % count
            if self.items[index].enabled:
                moved = index != self.selected
                self.selected = index
                return moved
        return False

    def handle_input(self, inp: InputHandler) -> str | None:
        """Обработва вход. Връща "move", "select" или None (за звуковите ефекти)."""
        result = None
        if inp.consume("up") and self.move(-1):
            result = "move"
        if inp.consume("down") and self.move(1):
            result = "move"
        if inp.consume("confirm") and self.items[self.selected].enabled:
            self.items[self.selected].action()
            result = "select"
        return result

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, top: int,
             spacing: int = 44, detail_font: pygame.font.Font | None = None) -> None:
        """Рисува редовете центрирани; избраният е подчертан със стрелки."""
        center_x = config.SCREEN_WIDTH // 2
        for index, item in enumerate(self.items):
            y = top + index * spacing
            selected = index == self.selected
            color = (config.MENU_SELECTED if selected else
                     config.MENU_NORMAL if item.enabled else config.MENU_DISABLED)
            text = f"›  {item.label}  ‹" if selected else item.label
            if item.detail and detail_font is not None:
                draw_text(surface, font, text, (center_x - 40, y), color, "midright")
                draw_text(surface, detail_font, item.detail, (center_x - 20, y), color,
                          "midleft")
            else:
                draw_text(surface, font, text, (center_x, y), color, "center")


class MenuBackground:
    """Анимиран фон на менютата: градиент, летящи искри и Искрица, която „диша“."""

    SPARKS = 40

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.gradient = vertical_gradient(config.SCREEN_WIDTH, config.SCREEN_HEIGHT,
                                          config.MENU_BG_TOP, config.MENU_BG_BOTTOM)
        self.time = 0.0

    def update(self, dt: float) -> None:
        """Напредва анимацията."""
        self.time += dt

    def draw(self, surface: pygame.Surface, show_hero: bool = True) -> None:
        """Рисува фона."""
        surface.blit(self.gradient, (0, 0))
        for index in range(self.SPARKS):
            speed = 20 + (index * 37) % 50
            x = (index * 173 + math.sin(self.time + index) * 20) % config.SCREEN_WIDTH
            y = config.SCREEN_HEIGHT - (self.time * speed + index * 97) % config.SCREEN_HEIGHT
            size = 2 + index % 3
            color = (255, 200 + index % 50, 120)
            pygame.draw.rect(surface, color, (round(x), round(y), size, size))
        if show_hero:
            frame = int(self.time * config.ANIMATION_FPS * 0.6)
            hero = pygame.transform.scale_by(self.assets.player("big", "idle", frame, 1), 2)
            surface.blit(hero, hero.get_rect(midbottom=(config.SCREEN_WIDTH // 2 - 300, 470)))
