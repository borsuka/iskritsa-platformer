"""Входна точка: `python main.py [--level 1-2] [--debug]`."""
from __future__ import annotations

import argparse
import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from engine.game import Game  # noqa: E402  (след настройката на средата)
from engine.states import Playing, new_session  # noqa: E402
from level.validator import use_utf8_console  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Чете аргументите от командния ред."""
    parser = argparse.ArgumentParser(description="Искрица: Пътят на светлината")
    parser.add_argument("--level", help="започни директно от ниво (напр. 2-1 или 3)")
    parser.add_argument("--debug", action="store_true", help="включи debug режим (F1)")
    return parser.parse_args()


def resolve_level(level_ids: list[str], wanted: str) -> str:
    """Превръща „2-1“ или пореден номер „3“ в идентификатор на ниво.

    Raises:
        ValueError: ако такова ниво няма.
    """
    if wanted in level_ids:
        return wanted
    if wanted.isdigit() and 1 <= int(wanted) <= len(level_ids):
        return level_ids[int(wanted) - 1]
    raise ValueError(f"няма ниво '{wanted}' (налични: {', '.join(level_ids)})")


def main() -> None:
    """Стартира играта."""
    use_utf8_console()
    args = parse_args()
    game = Game(debug=args.debug)
    if args.level:
        try:
            level_id = resolve_level(game.level_ids, args.level)
        except ValueError as error:
            sys.exit(f"Грешка: {error}")
        game.start(Playing(game, new_session(game, level_id)))
    else:
        game.start()
    game.run()


if __name__ == "__main__":
    main()
