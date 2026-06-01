from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL,
    due_date TEXT
);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        conn = self.connect()
        try:
            conn.executescript(SCHEMA_SQL)
            self._seed_settings(conn)
            self._seed_reference_data(conn)
            conn.commit()
        finally:
            conn.close()

    def _seed_settings(self, conn: sqlite3.Connection) -> None:
        defaults = {
            "theme": "dark",
            "daily_review_hour": "21",
            "weekly_review_day": "6",
            "monthly_review_day": "1",
            "xp_per_task": "10",
            "xp_per_streak_day": "3",
        }
        for key, value in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", (key, value))

    def _seed_reference_data(self, conn: sqlite3.Connection) -> None:
        del conn
