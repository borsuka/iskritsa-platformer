"""`Session` – прогресът през едно изиграване: животи, точки, монети, чекпойнт.

Сесията живее между нивата (за разлика от `World`, който се създава наново при
всяко възраждане). Не зависи от pygame.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import config


@dataclass
class Session:
    """Данните на текущата игра.

    Attributes:
        lives: оставащи животи.
        score: общ резултат.
        coins: монети (всеки `COINS_PER_EXTRA_LIFE` дават живот и броячът се нулира).
        level_ids: реда на нивата (напр. ["1-1", "1-2", ...]).
        level_index: индекс на текущото ниво в `level_ids`.
        checkpoint: (идентификатор на ниво, колона, ред) на последния запален чекпойнт.
        crystals: индексите на събраните в текущото ниво кристали.
        level_start_score: резултатът в началото на нивото (за рекорд на нивото).
    """

    lives: int = config.START_LIVES
    score: int = 0
    coins: int = 0
    level_ids: list[str] = field(default_factory=list)
    level_index: int = 0
    checkpoint: tuple[str, int, int] | None = None
    crystals: set[int] = field(default_factory=set)
    level_start_score: int = 0

    @property
    def level_id(self) -> str:
        """Идентификаторът на текущото ниво."""
        return self.level_ids[self.level_index] if self.level_ids else ""

    @property
    def level_score(self) -> int:
        """Точките, спечелени в текущото ниво."""
        return self.score - self.level_start_score

    def add_points(self, points: int) -> None:
        """Добавя точки към резултата."""
        self.score += points

    def add_coin(self) -> bool:
        """Добавя монета. Връща True, ако това е дало допълнителен живот."""
        self.coins += 1
        self.add_points(config.POINTS["coin"])
        if self.coins >= config.COINS_PER_EXTRA_LIFE:
            self.coins -= config.COINS_PER_EXTRA_LIFE
            self.lives += 1
            return True
        return False

    def lose_life(self) -> bool:
        """Отнема живот. Връща True, ако играта е свършила (Game Over)."""
        self.lives -= 1
        return self.lives <= 0

    def start_level(self, index: int) -> None:
        """Подготвя сесията за ново ниво (без чекпойнт и кристали)."""
        self.level_index = index
        self.checkpoint = None
        self.crystals = set()
        self.level_start_score = self.score

    @property
    def has_next_level(self) -> bool:
        """Има ли следващо ниво след текущото."""
        return self.level_index + 1 < len(self.level_ids)
