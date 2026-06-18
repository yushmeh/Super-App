import sqlite3
from pathlib import Path
from typing import Any

from core.app_paths import resolve_data_file

_DB_FILE = resolve_data_file(Path(__file__).parent, "media_tracker", "media.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS media_items (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    media_type   TEXT NOT NULL,            -- film | series | book | game
    status       TEXT NOT NULL,            -- planned | in_progress | completed
    rating       INTEGER,                  -- 1-10, NULL если не оценено
    notes        TEXT NOT NULL DEFAULT '',
    added_at     TEXT NOT NULL,            -- ISO дата добавления
    completed_at TEXT                      -- ISO дата завершения, NULL если не завершено
)
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(_CREATE_TABLE)


def fetch_all() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM media_items ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


def insert(item: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO media_items (id, title, media_type, status, rating,
                                     notes, added_at, completed_at)
            VALUES (:id, :title, :media_type, :status, :rating,
                    :notes, :added_at, :completed_at)
        """, item)


def update(item: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute("""
            UPDATE media_items SET
                title=:title, media_type=:media_type, status=:status,
                rating=:rating, notes=:notes, completed_at=:completed_at
            WHERE id=:id
        """, item)


def delete(item_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM media_items WHERE id=?", (item_id,))