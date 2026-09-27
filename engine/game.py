"""Основният цикъл на играта.

Всеки кадър:
1. прочитаме събитията от ОС (клавиши, затваряне на прозореца);
2. добавяме реалното изминало време в акумулатора (`FixedTimestep`);
3. изпълняваме логиката толкова пъти, колкото цели `FIXED_DT` са се натрупали;
4. рисуваме веднъж.
"""
from __future__ import annotations

import pygame

import config
from engine.input import InputHandler
from engine.states import MainMenu, State, StateMachine
from engine.timestep import FixedTimestep


class Game:
    """Притежава прозореца, входа и стека от екрани.

    Args:
        debug: дали да се стартира с включен debug режим.
    """

    def __init__(self, debug: bool = False) -> None:
        pygame.init()
        pygame.display.set_caption(config.GAME_TITLE)
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.font_big = pygame.font.Font(None, 64)
        self.input = InputHandler()
        self.input.resolve_keys()
        self.timestep = FixedTimestep()
        self.states = StateMachine()
        self.debug = debug
        self.running = True
        self.logic_steps = 0

    def start(self, state: State | None = None) -> None:
        """Задава първия екран (по подразбиране – главното меню)."""
        self.states.change(state if state is not None else MainMenu(self))

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
            self.states.update(self.timestep.step)
            self.input.end_step()
            self.logic_steps += 1
        self.states.draw(self.screen)
        pygame.display.flip()

    def run(self) -> None:
        """Основният цикъл – върти се, докато играчът не излезе."""
        if self.states.current is None:
            self.start()
        while self.running:
            frame_time = self.clock.tick(config.TARGET_FPS) / 1000.0
            self.process_events()
            self.step_frame(frame_time)
        pygame.quit()
