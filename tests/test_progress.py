"""Тестове за записа на прогреса (save.json)."""
from __future__ import annotations

import json

from level.progress import SaveData, load_progress, save_progress

IDS = ["1-1", "1-2", "2-1"]


def test_missing_file_creates_new_progress(tmp_path) -> None:
    """Липсващ файл → нов прогрес с отключено само първото ниво, и файлът се създава."""
    path = tmp_path / "save.json"
    data = load_progress(path, IDS)
    assert data.unlocked == ["1-1"]
    assert path.exists()


def test_corrupted_json_does_not_crash(tmp_path) -> None:
    """Повреден JSON не срива играта, а се заменя с нов прогрес."""
    path = tmp_path / "save.json"
    path.write_text("{това не е JSON", encoding="utf-8")
    data = load_progress(path, IDS)
    assert data.unlocked == ["1-1"]
    assert json.loads(path.read_text(encoding="utf-8"))["unlocked"] == ["1-1"]


def test_wrong_structure_does_not_crash(tmp_path) -> None:
    """Валиден JSON с грешна структура също се заменя."""
    path = tmp_path / "save.json"
    path.write_text('{"version": 1, "unlocked": 5, "levels": []}', encoding="utf-8")
    assert load_progress(path, IDS).unlocked == ["1-1"]


def test_progress_survives_save_and_load(tmp_path) -> None:
    """Прогресът се пази между стартиранията."""
    path = tmp_path / "save.json"
    data = SaveData.new(IDS)
    data.unlock("1-2")
    data.record("1-1", 4200, 95.5, {0, 3})
    assert save_progress(path, data)
    loaded = load_progress(path, IDS)
    assert loaded.unlocked == ["1-1", "1-2"]
    record = loaded.records["1-1"]
    assert (record.best_score, record.best_time, record.crystals) == (4200, 95.5, {0, 3})


def test_record_keeps_best_values() -> None:
    """Пазят се най-добрият резултат, най-доброто време и всички събрани кристали."""
    data = SaveData.new(IDS)
    assert data.record("1-1", 1000, 120.0, {0})
    assert not data.record("1-1", 800, 90.0, {2})
    record = data.records["1-1"]
    assert record.best_score == 1000
    assert record.best_time == 90.0
    assert record.crystals == {0, 2}


def test_unlock_is_idempotent() -> None:
    """Повторно отключване не дублира нивото."""
    data = SaveData.new(IDS)
    data.unlock("1-2")
    data.unlock("1-2")
    assert data.unlocked == ["1-1", "1-2"]
    assert data.is_unlocked("1-2") and not data.is_unlocked("2-1")
