"""Persistent task history. Tasks are records only; no background execution."""
from __future__ import annotations

from contextlib import closing

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


VALID_STATUSES = {"pending", "in_progress", "approval_required", "completed", "failed", "cancelled"}


class TaskStore:
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
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def create(self, title: str, notes: str = "") -> int:
        title = title.strip()
        if not title or len(title) > 300:
            raise ValueError("Task title must contain 1–300 characters.")
        if len(notes) > 4000:
            raise ValueError("Task notes are too long.")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "INSERT INTO tasks(title,status,notes,created_at,updated_at) VALUES(?,?,?,?,?)",
                (title, "pending", notes, now, now),
            )
            return int(cursor.lastrowid)

    def update_status(self, task_id: int, status: str, notes: str | None = None) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status. Choose: {', '.join(sorted(VALID_STATUSES))}")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            if notes is None:
                cursor = db.execute(
                    "UPDATE tasks SET status=?,updated_at=? WHERE id=?",
                    (status, now, task_id),
                )
            else:
                if len(notes) > 4000:
                    raise ValueError("Task notes are too long.")
                cursor = db.execute(
                    "UPDATE tasks SET status=?,notes=?,updated_at=? WHERE id=?",
                    (status, notes, now, task_id),
                )
            return cursor.rowcount > 0

    def list_tasks(self, limit: int = 50) -> list[dict[str, object]]:
        if not 1 <= limit <= 200:
            raise ValueError("Task list limit must be between 1 and 200.")
        with closing(self._connect()) as db, db:
            rows = db.execute(
                "SELECT id,title,status,notes,created_at,updated_at "
                "FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
