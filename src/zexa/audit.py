"""Small persistent audit trail with conservative secret redaction.

Audit events record decisions and outcomes, never credentials. This module is
stdlib-only and stores data locally in SQLite.
"""
from __future__ import annotations

from contextlib import closing

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any


_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|"
    r"authorization|cookie|otp|bridge[_-]?token|private[_-]?key)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_KEY_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+"
)
_MAX_DEPTH = 8
_MAX_STRING = 4000


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Redact sensitive fields recursively and bound arbitrary event payloads."""
    if _depth > _MAX_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        clean = {}
        for key, item in list(value.items())[:100]:
            safe_key = str(key)[:120]
            clean[safe_key] = "[REDACTED]" if _SENSITIVE_KEY.search(safe_key) else redact(
                item, _depth=_depth + 1
            )
        return clean
    if isinstance(value, (list, tuple)):
        return [redact(item, _depth=_depth + 1) for item in value[:100]]
    if isinstance(value, str):
        text = value[:_MAX_STRING]
        text = _BEARER.sub("Bearer [REDACTED]", text)
        return _KEY_VALUE.sub(lambda match: match.group(1) + "=[REDACTED]", text)
    if value is None or type(value) in (bool, int, float):
        return value
    return str(value)[:_MAX_STRING]


class AuditLog:
    """Append-only event log; callers should not store raw screen or message text."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(Path(database).expanduser())
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    details_json TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        return connection

    def record(
        self,
        event_type: str,
        *,
        actor: str = "user",
        action: str,
        decision: str,
        details: dict[str, Any] | None = None,
    ) -> int:
        fields = (event_type, actor, action, decision)
        if any(not isinstance(item, str) or not item.strip() or len(item) > 120 for item in fields):
            raise ValueError("Audit event labels must be non-empty strings of at most 120 characters.")
        safe_details = redact(details or {})
        encoded = json.dumps(safe_details, ensure_ascii=False, separators=(",", ":"))
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """INSERT INTO audit_events
                   (created_at, event_type, actor, action, decision, details_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (time.time(), event_type, actor, action, decision, encoded),
            )
            return int(cursor.lastrowid)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500.")
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """SELECT id, created_at, event_type, actor, action, decision, details_json
                   FROM audit_events ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0], "created_at": row[1], "event_type": row[2],
                "actor": row[3], "action": row[4], "decision": row[5],
                "details": json.loads(row[6]),
            }
            for row in rows
        ]
