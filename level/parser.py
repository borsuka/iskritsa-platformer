"""Превръщане на текстов файл в обект `Level`.

Форматът е описан подробно в LEVEL_FORMAT.md. Накратко:

    [meta]
    name = Зелената гора
    world = 1
    [map]
    ....C....
    P.......X
    #########

Парсерът е „толерантен“ (празни редове, редове с различна дължина), но
„строг“ към истинските грешки – всяка грешка съобщава файл, ред и колона.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import config
from level import tiles
from level.level import Level, LevelMeta, Spawn

#: Позволените ключове в секция [meta].
META_KEYS = ("name", "world", "time_limit", "background", "music")
MAP_COMMENT_PREFIX = "# "   # в [map] коментарът е „# “, защото „#“ е и земя
SECTIONS = ("meta", "map")


class LevelFormatError(Exception):
    """Грешка във формата на файл с ниво.

    Args:
        message: какво е грешно (на човешки език).
        source: име на файла.
        line: номер на ред (от 1), ако е известен.
        column: номер на колона (от 1), ако е известен.
    """

    def __init__(self, message: str, source: str = "<текст>",
                 line: int | None = None, column: int | None = None) -> None:
        self.message = message
        self.source = Path(source).name
        self.line = line
        self.column = column
        super().__init__(str(self))

    def __str__(self) -> str:
        parts = [self.source]
        if self.line is not None:
            parts.append(f"ред {self.line}")
        if self.column is not None:
            parts.append(f"колона {self.column}")
        return f"{', '.join(parts)}: {self.message}"


@dataclass
class _RawLevel:
    """Междинен резултат: суровите редове на двете секции."""

    meta: dict[str, tuple[str, int]] = field(default_factory=dict)
    map_lines: list[tuple[int, str]] = field(default_factory=list)
    seen_sections: set[str] = field(default_factory=set)


def find_level_files(directory: str | Path = config.LEVELS_DIR) -> list[Path]:
    """Всички файлове с нива в папка, подредени по име ("1-1", "1-2", "2-1"...)."""
    return sorted(Path(directory).glob(f"*{config.LEVEL_FILE_SUFFIX}"),
                  key=lambda path: [int(part) if part.isdigit() else part
                                    for part in path.stem.split("-")])


def load_level(path: str | Path) -> Level:
    """Зарежда ниво от файл.

    Raises:
        LevelFormatError: ако файлът липсва или съдържа грешка.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise LevelFormatError(f"файлът не може да бъде прочетен ({error})", str(path)) from error
    return parse_level(text, str(path))


def parse_level(text: str, source: str = "<текст>") -> Level:
    """Парсва текста на ниво.

    Args:
        text: съдържанието на файла.
        source: име на файла (използва се в съобщенията за грешка).

    Raises:
        LevelFormatError: при синтактична грешка.
    """
    raw = _split_sections(text, source)
    meta = _parse_meta(raw.meta, source)
    grid, spawns = _parse_map(raw.map_lines, source)
    return Level(meta=meta, grid=grid, spawns=spawns, source=source)


def _split_sections(text: str, source: str) -> _RawLevel:
    """Разделя текста на секции [meta] и [map] и пропуска коментарите."""
    raw = _RawLevel()
    section: str | None = None
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if _is_comment(stripped, section):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = _open_section(stripped, raw, source, line_no)
            continue
        if section is None:
            if stripped:
                raise LevelFormatError("очаква се секция [meta] или [map]", source, line_no, 1)
        elif section == "meta":
            if stripped:
                _read_meta_line(line, raw, source, line_no)
        else:
            raw.map_lines.append((line_no, line))
    if "map" not in raw.seen_sections:
        raise LevelFormatError("липсва секция [map]", source)
    return raw


def _is_comment(stripped: str, section: str | None) -> bool:
    """Решава дали редът е коментар (правилото е различно в [map])."""
    if section == "map":
        return stripped.startswith(MAP_COMMENT_PREFIX)
    return stripped.startswith("#")


def _open_section(stripped: str, raw: _RawLevel, source: str, line_no: int) -> str:
    """Обработва заглавие на секция като `[map]`."""
    name = stripped[1:-1].strip().lower()
    if name not in SECTIONS:
        raise LevelFormatError(f"непозната секция [{name}]", source, line_no, 1)
    if name in raw.seen_sections:
        raise LevelFormatError(f"секцията [{name}] се среща два пъти", source, line_no, 1)
    raw.seen_sections.add(name)
    return name


def _read_meta_line(line: str, raw: _RawLevel, source: str, line_no: int) -> None:
    """Чете ред `ключ = стойност` от [meta]."""
    if "=" not in line:
        column = len(line) - len(line.lstrip()) + 1
        raise LevelFormatError("очаква се 'ключ = стойност'", source, line_no, column)
    key, value = line.split("=", 1)
    key = key.strip().lower()
    if key not in META_KEYS:
        raise LevelFormatError(f"непознат ключ '{key}' (позволени: {', '.join(META_KEYS)})",
                               source, line_no, 1)
    if key in raw.meta:
        raise LevelFormatError(f"ключът '{key}' е зададен два пъти", source, line_no, 1)
    raw.meta[key] = (value.strip(), line_no)


def _parse_meta(values: dict[str, tuple[str, int]], source: str) -> LevelMeta:
    """Превръща текстовите стойности от [meta] в `LevelMeta` с проверка на типовете."""
    meta = LevelMeta(name=Path(source).stem)
    if "name" in values:
        meta.name = values["name"][0] or meta.name
    if "world" in values:
        meta.world = _parse_positive_int(values["world"], "world", source)
    if "time_limit" in values:
        meta.time_limit = _parse_positive_int(values["time_limit"], "time_limit", source)
    if "background" in values:
        background, line_no = values["background"]
        if background not in config.PALETTES:
            allowed = ", ".join(config.PALETTES)
            raise LevelFormatError(f"непознат фон '{background}' (позволени: {allowed})",
                                   source, line_no, 1)
        meta.background = background
    if "music" in values:
        meta.music = values["music"][0] or meta.music
    return meta


def _parse_positive_int(entry: tuple[str, int], key: str, source: str) -> int:
    """Чете цяло положително число от [meta]."""
    text, line_no = entry
    try:
        number = int(text)
    except ValueError:
        raise LevelFormatError(f"'{key}' трябва да е цяло число, а е '{text}'",
                               source, line_no, 1) from None
    if number <= 0:
        raise LevelFormatError(f"'{key}' трябва да е положително число", source, line_no, 1)
    return number


def _parse_map(map_lines: list[tuple[int, str]], source: str) -> tuple[list[list[str]],
                                                                       list[Spawn]]:
    """Превръща редовете на картата в решетка от тайлове и списък от обекти."""
    lines = _trim_blank_edges(map_lines)
    if not lines:
        raise LevelFormatError("секцията [map] е празна", source)
    width = max(len(text) for _, text in lines)
    grid: list[list[str]] = []
    spawns: list[Spawn] = []
    for row, (line_no, text) in enumerate(lines):
        grid_row: list[str] = []
        for col, symbol in enumerate(text.ljust(width, tiles.EMPTY)):
            if not tiles.is_file_symbol(symbol):
                shown = "интервал" if symbol == " " else f"'{symbol}'"
                raise LevelFormatError(f"непознат символ {shown}", source, line_no, col + 1)
            if symbol in tiles.ENTITY_SYMBOLS:
                kind = tiles.ENTITY_SYMBOLS[symbol]
                spawns.append(Spawn(kind, symbol, col, row, line_no, col + 1))
                symbol = tiles.EMPTY
            grid_row.append(symbol)
        grid.append(grid_row)
    return grid, spawns


def _trim_blank_edges(map_lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Маха празните редове в началото и края на картата.

    Празен ред в средата на картата се запазва и става ред от празни клетки.
    """
    start, end = 0, len(map_lines)
    while start < end and not map_lines[start][1].strip():
        start += 1
    while end > start and not map_lines[end - 1][1].strip():
        end -= 1
    return map_lines[start:end]
