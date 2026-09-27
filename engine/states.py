"""Екраните на играта, реализирани с шаблона State.

Всеки екран (меню, игра, пауза...) е отделен клас със същия интерфейс:
`enter`, `exit`, `update(dt)`, `draw(surface)`. `StateMachine` държи стек от
състояния – така паузата се „слага“ върху играта и я рисува отдолу.

Преходи:
    MainMenu → Playing | LevelSelect | Controls
    LevelSelect → Playing | MainMenu
    Playing → Pause (push) | LevelComplete | GameOver | Playing (загубен живот)
    Pause → Playing (pop) | Playing (рестарт) | MainMenu
    LevelComplete → Playing (следващо ниво) | Victory
    GameOver, Victory → MainMenu
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

import config
from engine.camera import Camera
from engine.effects import Effects
from engine.session import Session
from engine.world import COMPLETE, LIFE_LOST, World
from level.parser import level_file, load_level
from ui.hud import draw_text
from ui.menus import Menu, MenuItem

if TYPE_CHECKING:
    from engine.game import Game

TextRow = tuple[pygame.font.Font, str, tuple[int, int, int]]


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


def format_time(seconds: float | None) -> str:
    """Секунди → „м:сс“ (или „—“, ако няма време)."""
    if seconds is None:
        return "—"
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def new_session(game: Game, level_id: str | None = None) -> Session:
    """Нова сесия с всички нива; по желание започва от дадено ниво."""
    session = Session(level_ids=list(game.level_ids))
    if level_id is not None:
        session.start_level(game.level_ids.index(level_id))
    return session


# ---------------------------------------------------------------------------
# Менюта
# ---------------------------------------------------------------------------
class MenuState(State):
    """Общо за екраните с меню: анимиран фон, заглавие и навигация със звук."""

    title = ""
    subtitle = ""
    show_hero = True
    menu_top = 230

    def __init__(self, game: Game) -> None:
        super().__init__(game)
        self.menu = Menu(self.build_items())

    def build_items(self) -> list[MenuItem]:
        """Редовете на менюто (подкласовете ги задават)."""
        return []

    def update(self, dt: float) -> None:
        """Навигация; „назад“ (Esc) изпълнява `on_back`."""
        self.game.menu_background.update(dt)
        result = self.menu.handle_input(self.game.input)
        if result == "move":
            self.game.audio.play("menu_move")
        elif result == "select":
            self.game.audio.play("menu_select")
        elif self.game.input.consume("back"):
            self.on_back()

    def on_back(self) -> None:
        """Какво прави Esc (по подразбиране – нищо)."""

    def draw(self, surface: pygame.Surface) -> None:
        """Фон, заглавие, подзаглавие и менюто."""
        self.game.menu_background.draw(surface, self.show_hero)
        center_x = config.SCREEN_WIDTH // 2
        draw_text(surface, self.game.font_big, self.title, (center_x, 90), config.HUD_ACCENT,
                  "center")
        if self.subtitle:
            draw_text(surface, self.game.font_small, self.subtitle, (center_x, 140),
                      anchor="center")
        self.menu.draw(surface, self.game.font, self.menu_top, detail_font=self.game.font_small)


class MainMenu(MenuState):
    """Главното меню."""

    title = config.GAME_TITLE
    subtitle = "Върни светлината в Шепнещата гора, Кристалната пещера и Сенчестата крепост"

    def build_items(self) -> list[MenuItem]:
        """Нова игра, избор на ниво, контроли, изход."""
        return [
            MenuItem("Нова игра",
                     lambda: self.game.change_state(Playing(self.game, new_session(self.game)))),
            MenuItem("Избор на ниво", lambda: self.game.change_state(LevelSelect(self.game))),
            MenuItem("Контроли", lambda: self.game.change_state(Controls(self.game))),
            MenuItem("Изход", self.game.quit),
        ]


class LevelSelect(MenuState):
    """Избор на ниво – само отключените могат да се изберат."""

    title = "Избор на ниво"
    show_hero = False
    menu_top = 160

    def build_items(self) -> list[MenuItem]:
        """Ред за всяко ниво с рекорда му + „Назад“."""
        items = []
        for level_id in self.game.level_ids:
            level = load_level(level_file(level_id))
            unlocked = self.game.progress.is_unlocked(level_id)
            items.append(MenuItem(f"{level_id}  {level.meta.name}",
                                  lambda lid=level_id: self.start(lid), unlocked,
                                  self._record_text(level_id, unlocked,
                                                    len(level.spawns_of("crystal")))))
        items.append(MenuItem("Назад", self.on_back))
        return items

    def _record_text(self, level_id: str, unlocked: bool, total_crystals: int) -> str:
        """Текстът вдясно: заключено / рекорд / още не е минато."""
        if not unlocked:
            return "заключено"
        record = self.game.progress.records.get(level_id)
        if record is None:
            return "още не е минато"
        return (f"рекорд {record.best_score} · {format_time(record.best_time)} · "
                f"кристали {len(record.crystals)}/{total_crystals}")

    def start(self, level_id: str) -> None:
        """Започва избраното ниво с нова сесия."""
        self.game.change_state(Playing(self.game, new_session(self.game, level_id)))

    def on_back(self) -> None:
        """Връщане към главното меню."""
        self.game.change_state(MainMenu(self.game))


class Controls(MenuState):
    """Списък с контролите."""

    title = "Контроли"
    show_hero = False
    menu_top = 460
    LINES = (
        ("← →  /  A D", "движение"),
        ("Space  /  W  /  ↑", "скок (задръж за по-висок)"),
        ("Shift", "бягане"),
        ("X  /  J", "изстрел (с Пламък)"),
        ("↓ + скок", "пропадане през дъска"),
        ("Esc  /  P", "пауза"),
        ("F1", "debug режим"),
    )

    def build_items(self) -> list[MenuItem]:
        """Само „Назад“."""
        return [MenuItem("Назад", self.on_back)]

    def on_back(self) -> None:
        """Връщане към главното меню."""
        self.game.change_state(MainMenu(self.game))

    def draw(self, surface: pygame.Surface) -> None:
        """Таблица клавиш → действие."""
        super().draw(surface)
        center_x = config.SCREEN_WIDTH // 2
        for index, (keys, action) in enumerate(self.LINES):
            y = 160 + index * 40
            draw_text(surface, self.game.font, keys, (center_x - 20, y), config.MENU_SELECTED,
                      "midright")
            draw_text(surface, self.game.font, action, (center_x + 20, y), anchor="midleft")


# ---------------------------------------------------------------------------
# Игра
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LevelStats:
    """Резултатите от едно завършено ниво."""

    level_id: str
    name: str
    score: int
    time_bonus: int
    time_used: float
    crystals: int
    total_crystals: int
    new_record: bool = False


class Playing(State):
    """Играта: свят, камера, ефекти, звук, HUD, животи и възраждане.

    Args:
        game: обектът Game.
        session: текущата игра (животи, точки, ниво).
    """

    def __init__(self, game: Game, session: Session) -> None:
        super().__init__(game)
        self.session = session
        self.level = game.get_level(session.level_id)
        self.effects = Effects()
        self.world = self._create_world()
        self.camera = Camera(config.SCREEN_WIDTH, config.SCREEN_HEIGHT,
                             self.level.pixel_width, self.level.pixel_height)
        body = self.world.player.body
        self.camera.snap_to(body.center_x, body.center_y)
        self.finished = False

    def _create_world(self) -> World:
        """Създава света; ако има запален чекпойнт в това ниво – започва от него."""
        respawn = None
        checkpoint = self.session.checkpoint
        if checkpoint is not None and checkpoint[0] == self.level.level_id:
            respawn = next((spawn for spawn in self.level.spawns_of("checkpoint")
                            if (spawn.col, spawn.row) == checkpoint[1:]), None)
        return World(self.level, self.session, respawn)

    def update(self, dt: float) -> None:
        """Една стъпка на света, ефектите и камерата; реакция на край на живот/ниво."""
        inp = self.game.input
        if inp.consume("debug"):
            self.game.debug = not self.game.debug
        if inp.consume("pause") and not self.finished:
            self.game.audio.play("pause")
            self.game.states.push(Pause(self.game, self))
            return
        self.world.update(dt, inp.player_snapshot())
        self._handle_events()
        self.effects.update(dt)
        body = self.world.player.body
        self.camera.update(body.center_x, body.center_y, body.vx, dt)
        if not self.finished:
            self._handle_status()

    def _handle_events(self) -> None:
        """Събитията от света → частици, звуци, разклащане на камерата."""
        for event in self.world.drain_events():
            self.effects.on_event(event.kind, event.x, event.y, event.data)
            self.game.audio.play(event.kind)
            if event.kind == "boss_land":
                self.camera.shake()

    def _handle_status(self) -> None:
        """Загубен живот → възраждане или Game Over; завършено ниво → LevelComplete."""
        if self.world.status == LIFE_LOST:
            self.finished = True
            if self.session.lose_life():
                self.game.change_state(GameOver(self.game, self.session))
            else:
                self.game.change_state(Playing(self.game, self.session))
        elif self.world.status == COMPLETE:
            self.finished = True
            stats = self._finish_level()
            self.game.change_state(LevelComplete(self.game, self.session, stats))

    def _finish_level(self) -> LevelStats:
        """Бонус за време, запис на рекорда и отключване на следващото ниво."""
        bonus = int(self.world.time_left) * config.POINTS_PER_SECOND_LEFT
        self.session.add_points(bonus)
        time_used = self.level.meta.time_limit - self.world.time_left
        progress = self.game.progress
        new_record = progress.record(self.level.level_id, self.session.level_score, time_used,
                                     set(self.session.crystals))
        if self.session.has_next_level:
            progress.unlock(self.session.level_ids[self.session.level_index + 1])
        self.game.save()
        return LevelStats(self.level.level_id, self.level.meta.name, self.session.level_score,
                          bonus, time_used, len(self.session.crystals),
                          len(self.level.spawns_of("crystal")), new_record)

    def restart_level(self) -> None:
        """Рестарт от началото на нивото (от менюто за пауза)."""
        self.session.score = self.session.level_start_score
        self.session.start_level(self.session.level_index)
        self.game.change_state(Playing(self.game, self.session))

    def draw(self, surface: pygame.Surface) -> None:
        """Светът, ефектите и HUD-ът."""
        self.game.renderer.draw(surface, self.world, self.camera, self.game.debug,
                                self.game.clock.get_fps())
        self.effects.draw(surface, self.camera.offset, self.game.assets, self.game.font_small)
        self.game.hud.draw(surface, self.world, self.session)


class Pause(MenuState):
    """Пауза върху играта (overlay): продължи, рестартирай, към менюто."""

    is_overlay = True
    title = "Пауза"
    show_hero = False

    def __init__(self, game: Game, playing: Playing) -> None:
        self.playing = playing
        super().__init__(game)

    def build_items(self) -> list[MenuItem]:
        """Трите опции на паузата."""
        return [
            MenuItem("Продължи", self.resume),
            MenuItem("Рестартирай нивото", self.playing.restart_level),
            MenuItem("Главно меню", lambda: self.game.change_state(MainMenu(self.game))),
        ]

    def resume(self) -> None:
        """Маха паузата."""
        self.game.states.pop()

    def update(self, dt: float) -> None:
        """Esc/P отново продължава играта."""
        if self.game.input.consume("pause"):
            self.resume()
            return
        super().update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Затъмнява играта отдолу и рисува менюто."""
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))
        draw_text(surface, self.game.font_big, self.title, (config.SCREEN_WIDTH // 2, 150),
                  config.HUD_ACCENT, "center")
        self.menu.draw(surface, self.game.font, 250)


# ---------------------------------------------------------------------------
# Крайни екрани
# ---------------------------------------------------------------------------
class MessageScreen(State):
    """Екран с няколко реда текст и „Enter – продължи“."""

    def lines(self) -> list[TextRow]:
        """Редовете за показване (шрифт, текст, цвят)."""
        return []

    def on_confirm(self) -> None:
        """Какво става при Enter."""

    def update(self, dt: float) -> None:
        """Чака Enter."""
        self.game.menu_background.update(dt)
        if self.game.input.consume("confirm"):
            self.game.audio.play("menu_select")
            self.on_confirm()

    def draw(self, surface: pygame.Surface) -> None:
        """Фон и центрирани редове."""
        self.game.menu_background.draw(surface, False)
        rows = self.lines() + [(self.game.font_small, "Enter – продължи", config.MENU_SELECTED)]
        top = config.SCREEN_HEIGHT // 2 - len(rows) * 28
        for index, (font, text, color) in enumerate(rows):
            draw_text(surface, font, text, (config.SCREEN_WIDTH // 2, top + index * 56), color,
                      "center")


class LevelComplete(MessageScreen):
    """„Нивото е завършено“: точки, бонус, време, кристали."""

    def __init__(self, game: Game, session: Session, stats: LevelStats) -> None:
        super().__init__(game)
        self.session = session
        self.stats = stats

    def lines(self) -> list[TextRow]:
        """Статистика на нивото."""
        stats, font = self.stats, self.game.font
        rows = [
            (self.game.font_big, f"Ниво {stats.level_id} е завършено!", config.HUD_ACCENT),
            (font, stats.name, config.MENU_NORMAL),
            (font, f"Точки: {stats.score}   (бонус за време: {stats.time_bonus})",
             config.HUD_TEXT),
            (font, f"Време: {format_time(stats.time_used)}   "
                   f"Кристали: {stats.crystals} / {stats.total_crystals}", config.HUD_TEXT),
        ]
        if stats.new_record:
            rows.append((font, "Нов рекорд!", config.MENU_SELECTED))
        return rows

    def on_confirm(self) -> None:
        """Следващо ниво или финал."""
        if self.session.has_next_level:
            self.session.start_level(self.session.level_index + 1)
            self.game.change_state(Playing(self.game, self.session))
        else:
            self.game.change_state(Victory(self.game, self.session))


class GameOver(MessageScreen):
    """Край на играта (свършили са животите)."""

    def __init__(self, game: Game, session: Session) -> None:
        super().__init__(game)
        self.session = session

    def lines(self) -> list[TextRow]:
        """Надпис и резултат."""
        return [(self.game.font_big, "Край на играта", config.BOSS_BAR_FG),
                (self.game.font, f"Резултат: {self.session.score}", config.HUD_TEXT)]

    def on_confirm(self) -> None:
        """Към главното меню."""
        self.game.change_state(MainMenu(self.game))


class Victory(MessageScreen):
    """Финал: Сенкоглав е победен и светлината се връща."""

    def __init__(self, game: Game, session: Session) -> None:
        super().__init__(game)
        self.session = session

    def lines(self) -> list[TextRow]:
        """Поздравления и крайният резултат."""
        collected = sum(len(record.crystals) for record in self.game.progress.records.values())
        total = config.CRYSTALS_PER_LEVEL * len(self.game.level_ids)
        return [(self.game.font_big, "Победа!", config.HUD_ACCENT),
                (self.game.font, "Сенкоглав е победен и светлината се завърна.",
                 config.HUD_TEXT),
                (self.game.font, f"Краен резултат: {self.session.score}", config.HUD_TEXT),
                (self.game.font, f"Събрани кристали общо: {collected} / {total}",
                 config.HUD_TEXT)]

    def on_confirm(self) -> None:
        """Към главното меню."""
        self.game.change_state(MainMenu(self.game))
