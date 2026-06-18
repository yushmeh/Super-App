import json
from pathlib import Path
from typing import Any

from core.app_paths import resolve_data_file

_DATA_FILE = resolve_data_file(Path(__file__).parent, "budget_tracker", "budget_data.json")

_DEFAULT: dict[str, Any] = {"transactions": [], "categories": [], "goals": []}


def load() -> dict[str, Any]:
    """Загружает данные из JSON. При отсутствии файла возвращает пустую структуру."""
    if not _DATA_FILE.exists():
        return {k: list(v) for k, v in _DEFAULT.items()}
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in _DEFAULT.items():
            data.setdefault(key, list(val))
        return data
    except (json.JSONDecodeError, OSError):
        return {k: list(v) for k, v in _DEFAULT.items()}


def save(data: dict[str, Any]) -> None:
    with _DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)