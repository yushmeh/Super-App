"""
modules/budget_tracker/api/storage.py
======================================
Слой данных: JSON-персистентность бюджетного трекера.
Файл budget_data.json хранится рядом с этим модулем — данные
не теряются вне зависимости от рабочей директории запуска.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).parent / "budget_data.json"

_DEFAULT: dict[str, Any] = {
    "transactions": [],   # list[Transaction as dict]
    "categories":   [],   # list[Category as dict]
    "goals":        [],   # list[Goal as dict]
}


def load() -> dict[str, Any]:
    """Загружает данные из JSON-файла. Если файл отсутствует — возвращает дефолт."""
    if not _DATA_FILE.exists():
        return {k: list(v) if isinstance(v, list) else v for k, v in _DEFAULT.items()}
    try:
        with _DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Добавляем отсутствующие ключи (на случай обновления схемы)
        for key, val in _DEFAULT.items():
            data.setdefault(key, list(val) if isinstance(val, list) else val)
        return data
    except (json.JSONDecodeError, OSError):
        return {k: list(v) if isinstance(v, list) else v for k, v in _DEFAULT.items()}


def save(data: dict[str, Any]) -> None:
    """Сохраняет данные в JSON-файл."""
    with _DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)