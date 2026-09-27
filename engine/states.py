"""Екраните на играта, реализирани с шаблона State.

Всеки екран (меню, игра, пауза...) е отделен клас със същия интерфейс:
`enter`, `exit`, `update(dt)`, `draw(surface)`. `StateMachine` държи стек от
състояния – така паузата се „слага“ върху играта и я рисува отдолу.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import config

if TYPE_CHECKING:
    from engine.game import Game


class State:
    """Базов клас за екран на играта.

    Args:
        game: обектът `Game` – дава достъп до вход, шрифтове и смяна на екрани.
    """

    #: Ако е True, състоянието под него в стека също се рисува (напр. пауза).
    is_overlay = False

    def __init__(self, game: Game) -> None:
        self.game = game

    def enter(self) -> None:
        """Извиква се, когато състоянието стане активно."""

    def exit(self) -> None:
        """Извиква се, когато състоянието бъде премахнато."""

    def update(self, dt: float) -> None:
        """Обновява логиката с фиксирана стъпка `dt`."""

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува състоянието върху `surface`."""


class StateMachine:
    """Стек от състояния; активно е най-горното."""

    def __init__(self) -> None:
        self._stack: list[State] = []

    @property
    def current(self) -> State | None:
        """Активното състояние или None, ако стекът е празен."""
        return self._stack[-1] if self._stack else None

    def change(self, state: State) -> None:
        """Заменя целия стек с едно ново състояние."""
        while self._stack:
            self._stack.pop().exit()
        self._stack.append(state)
        state.enter()

    def push(self, state: State) -> None:
        """Слага състояние върху текущото (текущото замръзва)."""
        self._stack.append(state)
        state.enter()

    def pop(self) -> None:
        """Премахва най-горното състояние."""
        if self._stack:
            self._stack.pop().exit()

    def update(self, dt: float) -> None:
        """Обновява само активното състояние."""
        if self.current is not None:
            self.current.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува активното състояние и тези под него, ако то е overlay."""
        first = len(self._stack) - 1
        while first > 0 and self._stack[first].is_overlay:
            first -= 1
        for state in self._stack[first:]:
            state.draw(surface)


class MainMenu(State):
    """Главно меню (временна версия за етап 1)."""

    OPTIONS = ("Нова игра", "Изход")

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.selected = 0

    def update(self, dt: float) -> None:
        """Навигация с горе/долу, избор с Enter."""
        inp = self.game.input
        if inp.consume("up"):
            self.selected = (self.selected - 1) % len(self.OPTIONS)
        if inp.consume("down"):
            self.selected = (self.selected + 1) % len(self.OPTIONS)
        if inp.consume("confirm"):
            if self.selected == 0:
                self.game.states.change(Playing(self.game))
            else:
                self.game.quit()

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува заглавието и опциите."""
        surface.fill(config.MENU_BG_TOP)
        title = self.game.font_big.render(config.GAME_TITLE, True, config.HUD_ACCENT)
        surface.blit(title, title.get_rect(center=(config.SCREEN_WIDTH // 2, 150)))
        for index, text in enumerate(self.OPTIONS):
            color = config.MENU_SELECTED if index == self.selected else config.MENU_NORMAL
            label = self.game.font.render(text, True, color)
            surface.blit(label, label.get_rect(center=(config.SCREEN_WIDTH // 2, 280 + index * 44)))


class Playing(State):
    """Игра (временна версия за етап 1): правоъгълник, който се движи наляво/надясно."""

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.x = config.SCREEN_WIDTH / 2
        self.y = config.SCREEN_HEIGHT - 2 * config.TILE_SIZE - config.PLAYER_SMALL_HEIGHT

    def update(self, dt: float) -> None:
        """Мести героя с постоянна скорост, умножена по `dt`."""
        inp = self.game.input.player_snapshot()
        self.x += inp.direction * config.MAX_WALK_SPEED * dt
        self.x = max(0.0, min(self.x, config.SCREEN_WIDTH - config.PLAYER_WIDTH))
        if self.game.input.consume("pause"):
            self.game.states.change(MainMenu(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува земята и героя."""
        surface.fill(config.PALETTES["forest"]["sky_top"])
        ground_y = config.SCREEN_HEIGHT - 2 * config.TILE_SIZE
        pygame.draw.rect(surface, config.PALETTES["forest"]["ground"],
                         (0, ground_y, config.SCREEN_WIDTH, 2 * config.TILE_SIZE))
        pygame.draw.rect(surface, config.HUD_ACCENT,
                         (round(self.x), round(self.y),
                          config.PLAYER_WIDTH, config.PLAYER_SMALL_HEIGHT))
