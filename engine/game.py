"""Основният цикъл на играта.

Всеки кадър:
1. прочитаме събитията от ОС (клавиши, затваряне на прозореца);
2. добавяме реалното изминало време в акумулатора (`FixedTimestep`);
3. изпълняваме логиката толкова пъти, колкото цели `FIXED_DT` са се натрупали;
4. рисуваме веднъж.
"""
from __future__ import annotations

from pathlib import Path

import pygame

import config
from engine.assets import Assets
from engine.audio import Audio
from engine.input import InputHandler
from engine.renderer import Renderer
from engine.states import MainMenu, State, StateMachine
from engine.timestep import FixedTimestep
from level.level import Level
from level.parser import find_level_files, level_file, load_level
from level.progress import load_progress, save_progress
from level.validator import ensure_valid
from ui.hud import Hud
from ui.menus import MenuBackground
from ui.transitions import Fade


class Game:
    """Притежава прозореца, входа, звука, прогреса и стека от екрани.

    Args:
        debug: дали да се стартира с включен debug режим.
        audio_enabled: False изключва звука (напр. в тестове).
        save_path: къде да се пази прогресът (по подразбиране `config.SAVE_PATH`).
    """

    def __init__(self, debug: bool = False, audio_enabled: bool = True,
                 save_path: Path | None = None) -> None:
        pygame.init()
        pygame.display.set_caption(config.GAME_TITLE)
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.font_big = pygame.font.Font(None, 64)
        self.font_small = pygame.font.Font(None, 26)
        self.assets = Assets()
        pygame.display.set_icon(self.assets.player("small", "idle", 0, 1))
        self.renderer = Renderer(self.assets)
        self.hud = Hud(self.assets)
        self.menu_background = MenuBackground(self.assets)
        self.audio = Audio(audio_enabled)
        self.input = InputHandler()
        self.input.resolve_keys()
        self.timestep = FixedTimestep()
        self.states = StateMachine()
        self.fade = Fade()
        self.level_ids = [path.stem for path in find_level_files()]
        self._levels: dict[str, Level] = {}
        self.save_path = save_path or config.SAVE_PATH
        self.progress = load_progress(self.save_path, self.level_ids)
        self.debug = debug
        self.running = True
        self.logic_steps = 0

    def start(self, state: State | None = None) -> None:
        """Задава първия екран (по подразбиране – главното меню)."""
        self.states.change(state if state is not None else MainMenu(self))

    def get_level(self, level_id: str) -> Level:
        """Зарежда и валидира ниво само веднъж; после го връща от кеша.

        В играта се правят само бързите проверки (старт, изход, пропасти).
        Проверката за достижимост отнема 1–2 секунди, затова се пуска от тестовете
        и от инструмента `python -m level.validator` при създаване на ниво.

        Raises:
            LevelFormatError, LevelValidationError: ако нивото е невалидно.
        """
        if level_id not in self._levels:
            level = load_level(level_file(level_id))
            ensure_valid(level, check_reachability=False)
            self._levels[level_id] = level
        return self._levels[level_id]

    def change_state(self, state: State, fade: bool = True) -> None:
        """Сменя екрана – по подразбиране с плавно затъмняване."""
        if fade:
            self.fade.start(lambda: self.states.change(state))
        else:
            self.states.change(state)

    def save(self) -> None:
        """Записва прогреса на диска."""
        save_progress(self.save_path, self.progress)

    def quit(self) -> None:
        """Спира основния цикъл при следващия кадър."""
        self.running = False

    def process_events(self) -> None:
        """Обработва събитията от операционната система."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type in (pygame.KEYDOWN, pygame.KEYUP):
                self.input.handle_key(event.key, event.type == pygame.KEYDOWN)

    def step_frame(self, frame_time: float) -> None:
        """Изпълнява един кадър: логика с фиксирана стъпка и рисуване."""
        for _ in range(self.timestep.advance(frame_time)):
            if not self.fade.blocks_input:
                self.states.update(self.timestep.step)
            self.fade.update(self.timestep.step)
            self.input.end_step()
            self.logic_steps += 1
        self.states.draw(self.screen)
        self.fade.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        """Основният цикъл – върти се, докато играчът не излезе."""
        if self.states.current is None:
            self.start()
        while self.running:
            frame_time = self.clock.tick(config.TARGET_FPS) / 1000.0
            self.process_events()
            self.step_frame(frame_time)
        self.save()
        pygame.quit()
