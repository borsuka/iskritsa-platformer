"""Входна точка: `python main.py [--level 1-2] [--debug]`."""
from __future__ import annotations

import argparse
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from engine.game import Game  # noqa: E402  (след настройката на средата)


def parse_args() -> argparse.Namespace:
    """Чете аргументите от командния ред."""
    parser = argparse.ArgumentParser(description="Искрица: Пътят на светлината")
    parser.add_argument("--level", help="започни директно от ниво (напр. 2-1 или 3)")
    parser.add_argument("--debug", action="store_true", help="включи debug режим (F1)")
    return parser.parse_args()


def main() -> None:
    """Стартира играта."""
    args = parse_args()
    game = Game(debug=args.debug)
    game.start()
    game.run()


if __name__ == "__main__":
    main()
