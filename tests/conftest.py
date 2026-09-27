"""Общи настройки за тестовете: pygame работи без прозорец и без звук."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_save_file(tmp_path, monkeypatch) -> Path:
    """Всеки тест пише прогреса във временен файл, а не в истинския data/save.json."""
    path = tmp_path / "save.json"
    monkeypatch.setattr(config, "SAVE_PATH", path)
    return path
