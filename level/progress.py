"""Записване на прогреса в `data/save.json`: отключени нива и рекорди.

Формат на файла:

    {
      "version": 1,
      "unlocked": ["1-1", "1-2"],
      "levels": {
        "1-1": {"best_score": 4210, "best_time": 95.3, "crystals": [0, 2, 4]}
      }
    }

Повреден или липсващ файл НЕ срива играта: връща се нов прогрес и файлът се
презаписва. Записът е „атомарен“ – първо се пише във временен файл, после той
замества стария, за да не остане полузаписан JSON при спиране на тока.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

SAVE_VERSION = 1


@dataclass
class LevelRecord:
    """Рекордите за едно ниво."""

    best_score: int = 0
    best_time: float | None = None
    crystals: set[int] = field(default_factory=set)


@dataclass
class SaveData:
    """Целият записан прогрес."""

    unlocked: list[str] = field(default_factory=list)
    records: dict[str, LevelRecord] = field(default_factory=dict)

    @classmethod
    def new(cls, level_ids: list[str]) -> SaveData:
        """Нов прогрес: отключено е само първото ниво."""
        return cls(unlocked=level_ids[:1])

    def is_unlocked(self, level_id: str) -> bool:
        """Отключено ли е нивото."""
        return level_id in self.unlocked

    def unlock(self, level_id: str) -> None:
        """Отключва ниво (ако вече не е)."""
        if level_id not in self.unlocked:
            self.unlocked.append(level_id)

    def record(self, level_id: str, score: int, time_used: float, crystals: set[int]) -> bool:
        """Записва резултат от завършено ниво.

        Returns:
            True, ако резултатът е нов рекорд по точки.
        """
        entry = self.records.setdefault(level_id, LevelRecord())
        new_best = score > entry.best_score
        entry.best_score = max(entry.best_score, score)
        if entry.best_time is None or time_used < entry.best_time:
            entry.best_time = round(time_used, 2)
        entry.crystals |= crystals
        return new_best

    def to_json(self) -> dict:
        """Превръща прогреса в речник за JSON."""
        return {
            "version": SAVE_VERSION,
            "unlocked": list(self.unlocked),
            "levels": {level_id: {"best_score": record.best_score,
                                  "best_time": record.best_time,
                                  "crystals": sorted(record.crystals)}
                       for level_id, record in self.records.items()},
        }

    @classmethod
    def from_json(cls, data: dict) -> SaveData:
        """Създава прогрес от речник; при неправилна структура вдига ValueError."""
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            raise ValueError("непозната версия на записа")
        unlocked = data.get("unlocked", [])
        levels = data.get("levels", {})
        if not isinstance(unlocked, list) or not isinstance(levels, dict):
            raise ValueError("грешна структура")
        records = {}
        for level_id, entry in levels.items():
            best_time = entry.get("best_time")
            records[str(level_id)] = LevelRecord(
                best_score=int(entry.get("best_score", 0)),
                best_time=None if best_time is None else float(best_time),
                crystals={int(index) for index in entry.get("crystals", [])})
        return cls(unlocked=[str(level_id) for level_id in unlocked], records=records)


def load_progress(path: str | Path, level_ids: list[str]) -> SaveData:
    """Зарежда прогреса; при липсващ или повреден файл създава нов.

    Args:
        path: пътят до save.json.
        level_ids: всички нива (за да се отключи първото при нов прогрес).
    """
    path = Path(path)
    try:
        data = SaveData.from_json(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError, AttributeError):
        data = SaveData.new(level_ids)
        save_progress(path, data)
        return data
    if level_ids and not data.unlocked:
        data.unlock(level_ids[0])
    return data


def save_progress(path: str | Path, data: SaveData) -> bool:
    """Записва прогреса атомарно. Връща False, ако дискът не позволява запис."""
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(data.to_json(), ensure_ascii=False, indent=2),
                             encoding="utf-8")
        os.replace(temporary, path)
    except OSError:
        return False
    return True
