"""Тестове за аргументите на командния ред."""
from __future__ import annotations

import pytest

from main import resolve_level

IDS = ["1-1", "1-2", "2-1"]


def test_level_by_id_or_number() -> None:
    """--level приема идентификатор или пореден номер."""
    assert resolve_level(IDS, "1-2") == "1-2"
    assert resolve_level(IDS, "3") == "2-1"


@pytest.mark.parametrize("wanted", ["0", "4", "9-9", "abc"])
def test_unknown_level_is_error(wanted: str) -> None:
    """Непознато ниво дава ясна грешка."""
    with pytest.raises(ValueError, match="няма ниво"):
        resolve_level(IDS, wanted)
