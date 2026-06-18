import sqlite3
from pathlib import Path
from typing import Any

from core.app_paths import resolve_data_file

_DB_FILE = resolve_data_file(Path(__file__).parent, "schedule_tracker", "schedule.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS lessons (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    teacher     TEXT NOT NULL DEFAULT '',
    room        TEXT NOT NULL DEFAULT '',
    lesson_type TEXT NOT NULL DEFAULT 'lecture',
    day_of_week INTEGER NOT NULL,
    time_start  TEXT NOT NULL,
    time_end    TEXT NOT NULL,
    color       TEXT NOT NULL DEFAULT '#00D4FF',
    is_active   INTEGER NOT NULL DEFAULT 1
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицу если не существует."""
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)


def fetch_all() -> list[dict[str, Any]]:
    """Возвращает все занятия из БД."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM lessons ORDER BY day_of_week, time_start").fetchall()
    return [dict(r) for r in rows]


def insert(lesson: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO lessons (id, title, teacher, room, lesson_type,
                                 day_of_week, time_start, time_end, color, is_active)
            VALUES (:id, :title, :teacher, :room, :lesson_type,
                    :day_of_week, :time_start, :time_end, :color, :is_active)
        """, lesson)


def update(lesson: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE lessons SET
                title=:title, teacher=:teacher, room=:room,
                lesson_type=:lesson_type, day_of_week=:day_of_week,
                time_start=:time_start, time_end=:time_end,
                color=:color, is_active=:is_active
            WHERE id=:id
        """, lesson)


def delete(lesson_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))


def set_active(lesson_id: str, is_active: bool) -> None:
    with _connect() as conn:
        conn.execute("UPDATE lessons SET is_active=? WHERE id=?",
                     (1 if is_active else 0, lesson_id))