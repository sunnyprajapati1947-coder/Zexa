"""One-time, action-bound approval primitives.

Approvals are bound to an exact action and canonical payload, expire quickly,
and can be consumed only once. This module does not execute actions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
import time


@dataclass(frozen=True)
class ApprovalRequest:
    action: str
    explanation: str
    consequential: bool = True


@dataclass(frozen=True)
class ApprovalGrant:
    token: str
    action: str
    payload_sha256: str
    expires_at: float


def requires_approval(request: ApprovalRequest) -> bool:
    """Conservative default: consequential actions always require approval."""
    return request.consequential


def _fingerprint(action: str, payload: dict) -> str:
    if not isinstance(action, str) or not action.strip() or len(action) > 120:
        raise ValueError("Approval action must contain 1–120 characters.")
    if not isinstance(payload, dict):
        raise ValueError("Approval payload must be an object.")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded) > 32_000:
        raise ValueError("Approval payload exceeds the 32 KiB limit.")
    return hashlib.sha256((action + "\\0" + encoded).encode("utf-8")).hexdigest()


class ApprovalManager:
    """In-memory approval store; restart invalidates every outstanding grant."""

    def __init__(self, ttl_seconds: int = 120, clock=time.time) -> None:
        if not 1 <= ttl_seconds <= 600:
            raise ValueError("Approval TTL must be between 1 and 600 seconds.")
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._grants: dict[str, ApprovalGrant] = {}

    def issue(self, action: str, payload: dict, user_confirmed: bool) -> ApprovalGrant:
        if user_confirmed is not True:
            raise PermissionError("Explicit user confirmation is required.")
        fingerprint = _fingerprint(action, payload)
        now = self._clock()
        self._purge(now)
        token = secrets.token_urlsafe(32)
        grant = ApprovalGrant(token, action, fingerprint, now + self.ttl_seconds)
        self._grants[token] = grant
        return grant

    def consume(self, token: str, action: str, payload: dict) -> bool:
        if not isinstance(token, str):
            return False
        grant = self._grants.pop(token, None)
        if grant is None or grant.expires_at <= self._clock():
            return False
        try:
            fingerprint = _fingerprint(action, payload)
        except (TypeError, ValueError):
            return False
        return grant.action == action and secrets.compare_digest(grant.payload_sha256, fingerprint)

    def _purge(self, now: float) -> None:
        self._grants = {
            token: grant for token, grant in self._grants.items()
            if grant.expires_at > now
        }
