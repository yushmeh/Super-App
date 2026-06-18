import json
from pathlib import Path
from typing import Any

from core.app_paths import resolve_data_file

_DATA_FILE = resolve_data_file(Path(__file__).parent, "habit_tracker", "habits_data.json")


def load() -> dict[str, Any]:
    """Загружает данные из JSON. При отсутствии файла возвращает пустую структуру."""
    if not _DATA_FILE.exists():
        return {"habits": []}
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("habits", [])
        return data
    except (json.JSONDecodeError, OSError):
        return {"habits": []}


def save(data: dict[str, Any]) -> None:
    with _DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_to_file(data: dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_from_file(path: str) -> dict[str, Any]:
    """ValueError если формат файла неверный."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "habits" not in data or not isinstance(data["habits"], list):
        raise ValueError("Неверный формат файла: ожидается ключ 'habits' со списком")
    return data