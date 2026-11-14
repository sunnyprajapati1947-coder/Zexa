"""Central least-privilege policy and privacy-conscious audit log."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from .approvals import ApprovalManager, ApprovalRequest, requires_approval

_PERMISSION = re.compile(r"^[a-z][a-z0-9_.:-]{0,79}$")
_STATUSES = {"approval_required", "approval_issued", "allowed", "denied", "completed", "failed"}


class PermissionPolicy:
    """Default-deny permission set. Registration never grants permissions."""

    def __init__(self, granted: Iterable[str] = ()) -> None:
        self._granted: set[str] = set()
        for permission in granted:
            self.grant(permission)

    def grant(self, permission: str) -> None:
        if not isinstance(permission, str) or not _PERMISSION.fullmatch(permission):
            raise ValueError("Permission name is invalid.")
        self._granted.add(permission)

    def revoke(self, permission: str) -> bool:
        if permission not in self._granted:
            return False
        self._granted.remove(permission)
        return True

    def allows(self, permission: str) -> bool:
        return permission in self._granted

    def require(self, permissions: Iterable[str]) -> None:
        missing = sorted(set(permissions) - self._granted)
        if missing:
            raise PermissionError("Missing permissions: " + ", ".join(missing))

    def list_granted(self) -> list[str]:
        return sorted(self._granted)


class AuditLog:
    """SQLite audit trail that stores hashes, not raw action payloads."""

    def __init__(self, path: str | Path, clock=time.time) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_sha256 TEXT,
                    detail TEXT NOT NULL
                )"""
            )
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    def record(self, action: str, status: str, payload: dict | None = None,
               actor: str = "system", detail: str = "") -> int:
        if not isinstance(action, str) or not action.strip() or len(action) > 120:
            raise ValueError("Audit action must contain 1–120 characters.")
        if status not in _STATUSES:
            raise ValueError("Audit status is invalid.")
        if not isinstance(actor, str) or not actor.strip() or len(actor) > 80:
            raise ValueError("Audit actor must contain 1–80 characters.")
        if not isinstance(detail, str) or len(detail) > 500:
            raise ValueError("Audit detail must be at most 500 characters.")
        digest = None
        if payload is not None:
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if len(encoded) > 32_000:
                raise ValueError("Audit payload exceeds the 32 KiB limit.")
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO audit_events(timestamp, actor, action, status, payload_sha256, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (self._clock(), actor, action, status, digest, detail),
            )
            return int(cursor.lastrowid)

    def recent(self, limit: int = 20) -> list[dict]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Audit limit must be between 1 and 100.")
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, timestamp, actor, action, status, payload_sha256, detail "
                "FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]


class ActionGuard:
    """Combines default-deny permissions, one-time approval and audit recording."""

    def __init__(self, permissions: PermissionPolicy, approvals: ApprovalManager, audit: AuditLog) -> None:
        self.permissions = permissions
        self.approvals = approvals
        self.audit = audit

    def issue_approval(self, action: str, payload: dict, required_permissions: Iterable[str],
                       user_confirmed: bool, actor: str = "user"):
        try:
            self.permissions.require(required_permissions)
            grant = self.approvals.issue(action, payload, user_confirmed)
        except (PermissionError, ValueError) as exc:
            self.audit.record(action, "denied", payload, actor, str(exc)[:500])
            raise
        self.audit.record(action, "approval_issued", payload, actor, "One-time approval issued.")
        return grant

    def authorize(self, action: str, payload: dict, required_permissions: Iterable[str] = (),
                  consequential: bool = True, approval_token: str | None = None,
                  actor: str = "user") -> bool:
        try:
            self.permissions.require(required_permissions)
            if requires_approval(ApprovalRequest(action, "Action authorization", consequential)):
                if not approval_token or not self.approvals.consume(approval_token, action, payload):
                    raise PermissionError("A matching, unexpired, one-time approval is required.")
            elif approval_token and not self.approvals.consume(approval_token, action, payload):
                raise PermissionError("Approval token does not match this action.")
        except (PermissionError, ValueError) as exc:
            self.audit.record(action, "denied", payload, actor, str(exc)[:500])
            raise
        self.audit.record(action, "allowed", payload, actor, "Policy and approval checks passed.")
        return True
