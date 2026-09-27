"""Екраните на играта, реализирани с шаблона State.

Всеки екран (меню, игра, пауза...) е отделен клас със същия интерфейс:
`enter`, `exit`, `update(dt)`, `draw(surface)`. `StateMachine` държи стек от
състояния – така паузата се „слага“ върху играта и я рисува отдолу.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

import config
from engine.camera import Camera
from engine.effects import Effects
from engine.session import Session
from engine.world import COMPLETE, LIFE_LOST, World
from level.parser import find_level_files, load_level
from level.validator import ensure_valid

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


def new_session() -> Session:
    """Нова игра с всички нива от папката levels/."""
    return Session(level_ids=[path.stem for path in find_level_files()])


def level_path(level_id: str) -> str:
    """Пътят до файла на ниво по идентификатор."""
    return str(config.LEVELS_DIR / f"{level_id}{config.LEVEL_FILE_SUFFIX}")


class MainMenu(State):
    """Главно меню (временна версия; пълното меню е в етап 9)."""

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
                self.game.states.change(Playing(self.game, new_session()))
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
    """Играта: свят, камера, ефекти, животи и възраждане.

    Args:
        game: обектът Game.
        session: текущата игра (животи, точки, ниво).
    """

    def __init__(self, game: Game, session: Session) -> None:
        super().__init__(game)
        self.session = session
        self.level = load_level(level_path(session.level_id))
        ensure_valid(self.level)
        self.effects = Effects()
        self.small_font = pygame.font.Font(None, 26)
        self.world = self._create_world()
        self.camera = Camera(config.SCREEN_WIDTH, config.SCREEN_HEIGHT,
                             self.level.pixel_width, self.level.pixel_height)
        self._snap_camera()

    def _create_world(self) -> World:
        """Създава света; ако има запален чекпойнт в това ниво – започва от него."""
        respawn = None
        checkpoint = self.session.checkpoint
        if checkpoint is not None and checkpoint[0] == self.level.level_id:
            respawn = next((spawn for spawn in self.level.spawns_of("checkpoint")
                            if (spawn.col, spawn.row) == checkpoint[1:]), None)
        return World(self.level, self.session, respawn)

    def _snap_camera(self) -> None:
        """Центрира камерата върху героя."""
        body = self.world.player.body
        self.camera.snap_to(body.center_x, body.center_y)

    def update(self, dt: float) -> None:
        """Една стъпка на света, ефектите и камерата; реакция на край на живот/ниво."""
        inp = self.game.input
        if inp.consume("debug"):
            self.game.debug = not self.game.debug
        if inp.consume("pause"):
            self.game.states.change(MainMenu(self.game))
            return
        self.world.update(dt, inp.player_snapshot())
        for event in self.world.drain_events():
            self.effects.on_event(event.kind, event.x, event.y, event.data)
        self.effects.update(dt)
        body = self.world.player.body
        self.camera.update(body.center_x, body.center_y, body.vx, dt)
        self._handle_status()

    def _handle_status(self) -> None:
        """Загубен живот → възраждане или Game Over; завършено ниво → следващото."""
        if self.world.status == LIFE_LOST:
            if self.session.lose_life():
                self.game.states.change(GameOver(self.game, self.session))
                return
            self.world = self._create_world()
            self._snap_camera()
        elif self.world.status == COMPLETE:
            if self.session.has_next_level:
                self.session.start_level(self.session.level_index + 1)
                self.game.states.change(Playing(self.game, self.session))
            else:
                self.game.states.change(MainMenu(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        """Рисува света, ефектите и временен HUD."""
        self.game.renderer.draw(surface, self.world, self.camera, self.game.debug,
                                self.game.clock.get_fps())
        self.effects.draw(surface, self.camera.offset, self.game.assets, self.small_font)
        text = (f"Животи: {self.session.lives}   Точки: {self.session.score}   "
                f"Време: {int(self.world.time_left)}")
        surface.blit(self.small_font.render(text, True, config.HUD_TEXT), (12, 10))


class GameOver(State):
    """Край на играта: показва резултата; Enter връща в менюто."""

    def __init__(self, game: Game, session: Session) -> None:
        super().__init__(game)
        self.session = session

    def update(self, dt: float) -> None:
        """Чака потвърждение."""
        if self.game.input.consume("confirm"):
            self.game.states.change(MainMenu(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        """Надпис „Край на играта“ и резултат."""
        surface.fill(config.BLACK)
        center_x = config.SCREEN_WIDTH // 2
        title = self.game.font_big.render("Край на играта", True, config.BOSS_BAR_FG)
        surface.blit(title, title.get_rect(center=(center_x, 200)))
        score = self.game.font.render(f"Резултат: {self.session.score}", True, config.HUD_TEXT)
        surface.blit(score, score.get_rect(center=(center_x, 290)))
