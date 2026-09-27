"""Документацията не бива да лъже: примерите в нея се проверяват от тестове."""
from __future__ import annotations

from pathlib import Path

from level.parser import parse_level
from level.validator import validate_level

ROOT = Path(__file__).resolve().parent.parent


def test_level_format_example_is_valid() -> None:
    """Пълният пример в LEVEL_FORMAT.md е валидно и проходимо ниво."""
    text = (ROOT / "LEVEL_FORMAT.md").read_text(encoding="utf-8")
    example = text[text.index("## Пример"):]
    start = example.index("[meta]")
    end = example.index("```", start)
    report = validate_level(parse_level(example[start:end], "example.txt"))
    assert report.ok, report.errors
