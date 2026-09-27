"""Превръщане на клавиши в действия и буфериране на натисканията.

Играта никога не пита „натиснат ли е клавиш K_SPACE?“. Тя пита „натиснато ли е
действието `jump`?“. Така клавишите се сменят само в `config.KEY_BINDINGS`.

Има два вида информация:
* **задържани** действия (`is_held`) – клавишът е долу в момента;
* **натиснати** действия (`consume`) – клавишът е бил натиснат след последната
  логическа стъпка. Натискането се пази, докато някоя стъпка го „изконсумира“,
  затова бързо натискане между две стъпки на логиката не се губи.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import config


@dataclass(frozen=True)
class PlayerInput:
    """Моментна снимка на входа за една логическа стъпка на героя.

    Attributes:
        left: задържана посока наляво.
        right: задържана посока надясно.
        down: задържана посока надолу (за пропадане през платформа).
        run: задържано бягане.
        jump_held: задържан бутон за скок (за променлива височина).
        jump_pressed: скокът е натиснат в тази стъпка.
        shoot_pressed: изстрелът е натиснат в тази стъпка.
    """

    left: bool = False
    right: bool = False
    down: bool = False
    run: bool = False
    jump_held: bool = False
    jump_pressed: bool = False
    shoot_pressed: bool = False

    @property
    def direction(self) -> int:
        """Посока на движение: -1 наляво, 1 надясно, 0 никъде (или и двете)."""
        return int(self.right) - int(self.left)


class InputHandler:
    """Следи кои действия са задържани и кои са натиснати.

    Args:
        bindings: действие → имена на клавиши (виж `config.KEY_BINDINGS`).
    """

    def __init__(self, bindings: dict[str, tuple[str, ...]] | None = None) -> None:
        self._bindings = bindings if bindings is not None else config.KEY_BINDINGS
        self._key_to_actions: dict[int, list[str]] = {}
        self._held: set[str] = set()
        self._pressed: set[str] = set()

    def resolve_keys(self) -> None:
        """Превръща имената на клавиши в pygame кодове (изисква `pygame.init()`)."""
        import pygame  # локален импорт: логиката на входа не зависи от pygame

        self._key_to_actions.clear()
        for action, names in self._bindings.items():
            for name in names:
                code = pygame.key.key_code(name)
                self._key_to_actions.setdefault(code, []).append(action)

    def handle_key(self, key_code: int, is_down: bool) -> None:
        """Обработва натискане или пускане на физически клавиш."""
        for action in self._key_to_actions.get(key_code, []):
            if is_down:
                self.press(action)
            else:
                self.release(action)

    def press(self, action: str) -> None:
        """Отбелязва действие като натиснато и задържано."""
        if action not in self._held:
            self._pressed.add(action)
        self._held.add(action)

    def release(self, action: str) -> None:
        """Отбелязва действие като пуснато."""
        self._held.discard(action)

    def set_held(self, actions: Iterable[str]) -> None:
        """Задава точно кои действия са задържани (за скриптиран вход в тестове)."""
        wanted = set(actions)
        for action in wanted - self._held:
            self.press(action)
        for action in self._held - wanted:
            self.release(action)

    def is_held(self, action: str) -> bool:
        """Връща дали действието е задържано в момента."""
        return action in self._held

    def peek(self, action: str) -> bool:
        """Връща дали действието е натиснато, без да го изконсумира."""
        return action in self._pressed

    def consume(self, action: str) -> bool:
        """Връща дали действието е натиснато и го изчиства (еднократно събитие)."""
        if action in self._pressed:
            self._pressed.discard(action)
            return True
        return False

    def player_snapshot(self) -> PlayerInput:
        """Създава `PlayerInput` за една стъпка и изконсумира скока и изстрела."""
        return PlayerInput(
            left=self.is_held("left"),
            right=self.is_held("right"),
            down=self.is_held("down"),
            run=self.is_held("run"),
            jump_held=self.is_held("jump"),
            jump_pressed=self.consume("jump"),
            shoot_pressed=self.consume("shoot"),
        )

    def end_step(self) -> None:
        """Изчиства неизползваните натискания след логическа стъпка.

        Без това натискане на „X“ в менюто би стреляло по-късно в нивото.
        """
        self._pressed.clear()

    def clear(self) -> None:
        """Забравя всичко (например при смяна на екран)."""
        self._pressed.clear()
        self._held.clear()
