"""Нивата: тайлове, парсер, валидатор, достижимост и запис на прогреса."""
from __future__ import annotations

import os

# Инструментът `python -m level.validator` не бива да печата банера на pygame.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
