"""Local SQLite memory store with explicit user-controlled persistence.

Only information explicitly passed to remember() is stored. This module does
not scrape chats, contacts, files, or device data.
"""
from __future__ import annotations

from contextlib import closing

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, path: str | Path = "data/zexa.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def remember(self, key: str, value: str) -> int:
        key, value = key.strip(), value.strip()
        if not key or len(key) > 120:
            raise ValueError("Memory key must contain 1–120 characters.")
        if not value or len(value) > 4000:
            raise ValueError("Memory value must contain 1–4000 characters.")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            db.execute("""
                INSERT INTO memories(key, value, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value, updated_at=excluded.updated_at
            """, (key, value, now, now))
            row = db.execute("SELECT id FROM memories WHERE key=?", (key,)).fetchone()
            return int(row["id"])

    def recall(self, key: str) -> dict[str, str] | None:
        with closing(self._connect()) as db, db:
            row = db.execute(
                "SELECT key, value, created_at, updated_at FROM memories WHERE key=?",
                (key.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def list_memories(self) -> list[dict[str, str]]:
        with closing(self._connect()) as db, db:
            rows = db.execute(
                "SELECT key, value, created_at, updated_at FROM memories ORDER BY key"
            ).fetchall()
        return [dict(row) for row in rows]

    def forget(self, key: str) -> bool:
        with closing(self._connect()) as db, db:
            cursor = db.execute("DELETE FROM memories WHERE key=?", (key.strip(),))
            return cursor.rowcount > 0

    def clear(self) -> int:
        with closing(self._connect()) as db, db:
            cursor = db.execute("DELETE FROM memories")
            return cursor.rowcount
