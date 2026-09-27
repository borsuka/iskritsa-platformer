"""Смислови проверки на заредено ниво.

Парсерът проверява *синтаксиса* (познати символи, правилни секции). Валидаторът
проверява *смисъла*: има ли точно един старт и един изход, не стои ли героят над
пропаст, може ли изходът изобщо да бъде достигнат и т.н.

Грешките правят нивото неизползваемо; предупрежденията само обръщат внимание
(напр. „в нивото има 4 кристала, а се очакват 5“).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import config
from level.level import Level, Spawn


@dataclass
class ValidationReport:
    """Резултат от валидацията."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True, ако няма грешки (предупрежденията са позволени)."""
        return not self.errors


class LevelValidationError(Exception):
    """Нивото е синтактично вярно, но не може да се играе."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        super().__init__("\n".join(report.errors))


def validate_level(level: Level) -> ValidationReport:
    """Изпълнява всички проверки и връща отчет.

    Args:
        level: заредено ниво.
    """
    report = ValidationReport()
    _check_exactly_one(level, "player", "старт 'P'", report)
    _check_exactly_one(level, "exit", "изход 'X'", report)
    _check_at_most_one(level, "boss", "бос '@'", report)
    _check_not_over_pit(level, report)
    _check_crystals(level, report)
    return report


def ensure_valid(level: Level) -> None:
    """Вдига `LevelValidationError`, ако нивото има грешки."""
    report = validate_level(level)
    if not report.ok:
        raise LevelValidationError(report)


def _check_exactly_one(level: Level, kind: str, label: str, report: ValidationReport) -> None:
    """Проверява, че обект от даден вид се среща точно веднъж."""
    found = level.spawns_of(kind)
    if not found:
        report.errors.append(f"{level.file_name}: липсва {label}")
        return
    _report_duplicates(level, found, label, report)


def _check_at_most_one(level: Level, kind: str, label: str, report: ValidationReport) -> None:
    """Проверява, че обект от даден вид се среща най-много веднъж."""
    _report_duplicates(level, level.spawns_of(kind), label, report)


def _report_duplicates(level: Level, found: list[Spawn], label: str,
                       report: ValidationReport) -> None:
    """Добавя грешка за всяко повторение след първото."""
    first = found[0] if found else None
    for extra in found[1:]:
        report.errors.append(
            f"{level.location(extra.line, extra.column)}: втори {label} "
            f"(първият е на ред {first.line}, колона {first.column})")


def find_pit_columns(level: Level) -> list[int]:
    """Колоните, в които няма нищо, на което да се стъпи – падането там е смърт."""
    return [col for col in range(level.width)
            if not any(level.tile_at(col, row).supports_standing for row in range(level.height))]


def _has_ground_below(level: Level, spawn: Spawn) -> bool:
    """Има ли под обекта (в неговата колона) нещо, на което да се стъпи."""
    return any(level.tile_at(spawn.col, row).supports_standing
               for row in range(spawn.row + 1, level.height))


def _check_not_over_pit(level: Level, report: ValidationReport) -> None:
    """Старт, изход и чекпойнти не бива да висят над пропаст.

    Пропастите по принцип са позволени и умишлени: под тях няма нищо и падането
    води до загуба на живот. Но старт над пропаст би убивал героя веднага.
    """
    for kind, label in (("player", "старт 'P'"), ("exit", "изход 'X'"),
                        ("checkpoint", "чекпойнт 'K'")):
        for spawn in level.spawns_of(kind):
            if not _has_ground_below(level, spawn):
                report.errors.append(
                    f"{level.location(spawn.line, spawn.column)}: {label} е над пропаст")


def _check_crystals(level: Level, report: ValidationReport) -> None:
    """Предупреждава, ако броят големи кристали не е стандартният."""
    count = len(level.spawns_of("crystal"))
    if count != config.CRYSTALS_PER_LEVEL:
        report.warnings.append(
            f"{level.file_name}: {count} кристала "
            f"(очакват се {config.CRYSTALS_PER_LEVEL})")
