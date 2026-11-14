"""Durable, allowlisted background job queue backed by SQLite.

Jobs store data only; handlers are supplied by trusted application code. No
shell command, Python expression, or model-generated code is ever executed.
"""
from __future__ import annotations

from contextlib import closing

import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


JobHandler = Callable[[dict], str]
_KIND = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
_SAFE_ERROR = re.compile(r"^[A-Za-z][A-Za-z0-9_.]{0,79}$")


class JobQueue:
    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("ZEXA_JOB_DB") or (Path.home() / ".zexa" / "jobs.sqlite3")
        self.path = Path(configured).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    run_at TEXT NOT NULL,
                    result TEXT NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_due ON jobs(status, run_at, id)"
            )

    def enqueue(
        self,
        kind: str,
        payload: dict,
        run_at: datetime | None = None,
        max_attempts: int = 3,
    ) -> int:
        if not isinstance(kind, str) or not _KIND.fullmatch(kind):
            raise ValueError("Job kind must be a lowercase identifier.")
        if not isinstance(payload, dict):
            raise ValueError("Job payload must be a JSON object.")
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10.")
        try:
            encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Job payload must contain valid JSON data.") from exc
        if len(encoded) > 8000:
            raise ValueError("Job payload is too large.")
        scheduled = run_at or datetime.now(timezone.utc)
        if scheduled.tzinfo is None or scheduled.utcoffset() is None:
            raise ValueError("run_at must include a timezone.")
        scheduled = scheduled.astimezone(timezone.utc).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                """INSERT INTO jobs(kind,payload,status,attempts,max_attempts,
                   run_at,created_at,updated_at) VALUES(?,?, 'pending',0,?,?,?,?)""",
                (kind, encoded, max_attempts, scheduled, now, now),
            )
            return int(cursor.lastrowid)

    def claim_due(self) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                """SELECT * FROM jobs WHERE status='pending' AND run_at<=?
                   AND attempts<max_attempts ORDER BY run_at,id LIMIT 1""",
                (now,),
            ).fetchone()
            if row is None:
                db.commit()
                return None
            changed = db.execute(
                """UPDATE jobs SET status='running',attempts=attempts+1,updated_at=?
                   WHERE id=? AND status='pending'""",
                (now, row["id"]),
            ).rowcount
            db.commit()
            if changed != 1:
                return None
            item = dict(row)
            item["attempts"] += 1
            item["payload"] = json.loads(item["payload"])
            return item

    def complete(self, job_id: int, result: str = "") -> None:
        if len(result) > 4000:
            result = result[:4000]
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            changed = db.execute(
                """UPDATE jobs SET status='completed',result=?,last_error='',
                   updated_at=? WHERE id=? AND status='running'""",
                (result, now, job_id),
            ).rowcount
            if changed != 1:
                raise ValueError("Job is not currently running.")

    def fail(self, job: dict, error: str, retryable: bool = True) -> str:
        now = datetime.now(timezone.utc).isoformat()
        retry = retryable and job["attempts"] < job["max_attempts"]
        status = "pending" if retry else "failed"
        safe_error = error if isinstance(error, str) and _SAFE_ERROR.fullmatch(error) else "JobError"
        with closing(self._connect()) as db, db:
            db.execute(
                """UPDATE jobs SET status=?,last_error=?,updated_at=?
                   WHERE id=? AND status='running'""",
                (status, safe_error, now, job["id"]),
            )
        return status

    def recover_stale(self, lease_seconds: int = 300) -> int:
        if not 30 <= lease_seconds <= 86400:
            raise ValueError("lease_seconds must be between 30 and 86400.")
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=lease_seconds)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                """UPDATE jobs SET status=CASE WHEN attempts<max_attempts
                       THEN 'pending' ELSE 'failed' END, updated_at=?
                   WHERE status='running' AND updated_at<?""",
                (now, cutoff),
            )
            return cursor.rowcount

    def cancel(self, job_id: int) -> bool:
        """Cancel a pending job; running/completed jobs are never silently interrupted."""
        if type(job_id) is not int or job_id < 1:
            raise ValueError("job_id must be a positive integer.")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            changed = db.execute(
                "UPDATE jobs SET status='cancelled',updated_at=? WHERE id=? AND status='pending'",
                (now, job_id),
            ).rowcount
            return changed == 1

    def retry(self, job_id: int) -> bool:
        """Requeue a failed job with its original validated data and fresh attempt budget."""
        if type(job_id) is not int or job_id < 1:
            raise ValueError("job_id must be a positive integer.")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as db, db:
            changed = db.execute(
                """UPDATE jobs SET status='pending',attempts=0,last_error='',
                   run_at=?,updated_at=? WHERE id=? AND status='failed'""",
                (now, now, job_id),
            ).rowcount
            return changed == 1

    def list_jobs(self, limit: int = 50) -> list[dict]:
        if not 1 <= limit <= 200:
            raise ValueError("Job list limit must be between 1 and 200.")
        with closing(self._connect()) as db, db:
            rows = db.execute(
                """SELECT id,kind,status,attempts,max_attempts,run_at,result,
                   last_error,created_at,updated_at FROM jobs ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


class JobWorker:
    def __init__(self, queue: JobQueue, handlers: dict[str, JobHandler]) -> None:
        self.queue = queue
        self.handlers = dict(handlers)

    def run_once(self) -> str:
        job = self.queue.claim_due()
        if job is None:
            return "idle"
        handler = self.handlers.get(job["kind"])
        if handler is None:
            self.queue.fail(job, f"No handler registered for job kind: {job['kind']}", retryable=False)
            return "failed"
        try:
            result = handler(job["payload"])
            self.queue.complete(job["id"], str(result or ""))
            return "completed"
        except Exception as exc:
            # Exception messages can contain user text, provider responses, or secrets.
            # Persist only the exception class, never its potentially sensitive message.
            retryable = not isinstance(exc, (PermissionError, ValueError, KeyError, TypeError))
            return self.queue.fail(job, type(exc).__name__, retryable=retryable)
