from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True если приложение запущено как собранный .exe (PyInstaller)."""
    return getattr(sys, "frozen", False)


def get_user_data_dir(module_name: str) -> Path:
    """
    Возвращает директорию для постоянного хранения данных модуля.
    """
    if not is_frozen():
        return None  # type: ignore[return-value]

    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "SuperApp"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "SuperApp"
    else:
        base = Path.home() / ".local" / "share" / "SuperApp"

    target = base / module_name
    target.mkdir(parents=True, exist_ok=True)
    return target


def resolve_data_file(dev_path: Path, module_name: str, filename: str) -> Path:
    """
    Возвращает путь к файлу данных: постоянная папка пользователя в .exe,
    либо путь рядом с исходниками в режиме разработки.
    """
    if is_frozen():
        user_dir = get_user_data_dir(module_name)
        return user_dir / filename
    return dev_path / filename