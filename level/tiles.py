"""Типове тайлове и значението на всеки символ в текстовия файл на нивото.

Символите са два вида:
* **тайлове** – остават в решетката на картата (земя, платформи, шипове...);
* **обекти (entities)** – при зареждане на мястото им остава празен тайл `.`, а
  в нивото се записва „точка на появяване“ (spawn) – герой, враг, монета...
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TileType:
    """Свойства на един вид тайл.

    Attributes:
        symbol: символът във файла.
        name: човешко име (за документация и съобщения за грешка).
        solid: блокира движение от всички страни.
        one_way: може да се стъпи отгоре, но се минава отдолу и отстрани.
        hazard: наранява героя при допир (шипове).
        deadly: убива героя моментално (лава).
        bumpable: пуска съдържание при удар отдолу (блок с изненада).
        breakable: чупи се при удар отдолу от голямата форма.
        in_files: може ли символът да се пише във файл (иначе е вътрешен).
    """

    symbol: str
    name: str
    solid: bool = False
    one_way: bool = False
    hazard: bool = False
    deadly: bool = False
    bumpable: bool = False
    breakable: bool = False
    in_files: bool = True

    @property
    def supports_standing(self) -> bool:
        """Може ли да се стои отгоре на този тайл."""
        return self.solid or self.one_way


EMPTY = "."
SOLID = "#"
ONE_WAY = "="
SURPRISE = "?"
SURPRISE_POWERUP = "!"
SURPRISE_COMET = "*"
SURPRISE_LIFE = "+"
BREAKABLE = "B"
SPIKES = "^"
LAVA = "~"
USED_BLOCK = "u"  # вътрешен: блок с изненада, който вече е празен

TILE_TYPES: dict[str, TileType] = {
    EMPTY: TileType(EMPTY, "празно"),
    SOLID: TileType(SOLID, "твърд блок", solid=True),
    ONE_WAY: TileType(ONE_WAY, "one-way платформа", one_way=True),
    SURPRISE: TileType(SURPRISE, "блок с изненада (монета)", solid=True, bumpable=True),
    SURPRISE_POWERUP: TileType(SURPRISE_POWERUP, "блок с изненада (сила)", solid=True,
                               bumpable=True),
    SURPRISE_COMET: TileType(SURPRISE_COMET, "блок с изненада (комета)", solid=True,
                             bumpable=True),
    SURPRISE_LIFE: TileType(SURPRISE_LIFE, "блок с изненада (живот)", solid=True,
                            bumpable=True),
    BREAKABLE: TileType(BREAKABLE, "чуплив блок", solid=True, breakable=True),
    SPIKES: TileType(SPIKES, "шипове", hazard=True),
    LAVA: TileType(LAVA, "лава", deadly=True),
    USED_BLOCK: TileType(USED_BLOCK, "празен блок", solid=True, in_files=False),
}

#: Какво пуска всеки блок с изненада.
SURPRISE_CONTENTS: dict[str, str] = {
    SURPRISE: "coin",
    SURPRISE_POWERUP: "powerup",
    SURPRISE_COMET: "comet",
    SURPRISE_LIFE: "life",
}

#: Символ на обект → вид на обекта.
ENTITY_SYMBOLS: dict[str, str] = {
    "P": "player",
    "X": "exit",
    "K": "checkpoint",
    "C": "coin",
    "G": "crystal",
    "E": "walker",
    "H": "hopper",
    "F": "flyer",
    "S": "shooter",
    "M": "platform_h",
    "V": "platform_v",
    "D": "platform_falling",
    "@": "boss",
}

#: Кои видове обекти са врагове.
ENEMY_KINDS = frozenset({"walker", "hopper", "flyer", "shooter", "boss"})


def tile_type(symbol: str) -> TileType:
    """Връща типа на тайл по символ (непознатите се третират като празно)."""
    return TILE_TYPES.get(symbol, TILE_TYPES[EMPTY])


def is_file_symbol(symbol: str) -> bool:
    """Връща дали символът е позволен във файл на ниво."""
    known_tile = symbol in TILE_TYPES and TILE_TYPES[symbol].in_files
    return known_tile or symbol in ENTITY_SYMBOLS
