"""Автоматична проверка на конвенциите от CLAUDE.md.

Така правилата не са само пожелание: ако някой добави ред от 120 символа или
функция без docstring, тестовете го хващат.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ("engine", "entities", "level", "physics", "ui")
MAX_LINE = 100
MAX_FUNCTION_LINES = 45   # „до ~40 реда“ + малък толеранс

SOURCE_FILES = sorted([ROOT / "main.py", ROOT / "config.py"]
                      + [path for folder in SOURCE_DIRS
                         for path in (ROOT / folder).glob("*.py")])
ALL_PY_FILES = SOURCE_FILES + sorted((ROOT / "tests").glob("*.py"))


def relative(path: Path) -> str:
    """Път спрямо корена на проекта (за четими съобщения)."""
    return str(path.relative_to(ROOT))


@pytest.mark.parametrize("path", ALL_PY_FILES, ids=relative)
def test_lines_are_at_most_100_characters(path: Path) -> None:
    """PEP 8 с ограничение 100 символа на ред."""
    long_lines = [number for number, line in
                  enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
                  if len(line) > MAX_LINE]
    assert not long_lines, f"{relative(path)}: твърде дълги редове {long_lines}"


@pytest.mark.parametrize("path", ALL_PY_FILES, ids=relative)
def test_future_annotations(path: Path) -> None:
    """Всеки непразен модул започва с `from __future__ import annotations`."""
    text = path.read_text(encoding="utf-8")
    if text.strip():
        assert "from __future__ import annotations" in text


def public_definitions(tree: ast.Module):
    """Всички публични класове и функции/методи в модула."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if not node.name.startswith("_") or node.name == "__init__":
                yield node


@pytest.mark.parametrize("path", SOURCE_FILES, ids=relative)
def test_public_definitions_have_docstrings(path: Path) -> None:
    """Всеки публичен клас и функция има docstring (без __init__ – описан е в класа)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assert ast.get_docstring(tree), f"{relative(path)}: модулът няма docstring"
    missing = [node.name for node in public_definitions(tree)
               if node.name != "__init__" and not ast.get_docstring(node)]
    assert not missing, f"{relative(path)}: без docstring: {missing}"


@pytest.mark.parametrize("path", SOURCE_FILES, ids=relative)
def test_functions_are_short(path: Path) -> None:
    """Функциите са до ~40 реда."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    too_long = [f"{node.name} ({node.end_lineno - node.lineno + 1} реда)"
                for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                and node.end_lineno - node.lineno + 1 > MAX_FUNCTION_LINES]
    assert not too_long, f"{relative(path)}: {too_long}"


LOGIC_DIRS = ("physics", "level")


@pytest.mark.parametrize("path", sorted(path for folder in LOGIC_DIRS
                                        for path in (ROOT / folder).glob("*.py")), ids=relative)
def test_logic_does_not_use_display(path: Path) -> None:
    """Физиката, парсерът и валидаторът не зависят от дисплей."""
    text = path.read_text(encoding="utf-8")
    assert "pygame.display" not in text
    assert "pygame.draw" not in text
