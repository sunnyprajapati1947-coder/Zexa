"""Guarded synchronous execution gateway for registered Zexa capabilities.

The gateway composes permission decisions, one-time action-bound approvals, and
persistent audit events. Tool handlers must be supplied by trusted application
code; model output must never supply a Python callable.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .approvals import ApprovalManager
from .audit import AuditLog
from .policy import PermissionPolicy


class ExecutionDenied(PermissionError):
    """Raised when policy or approval checks reject an action."""


class ExecutionGateway:
    def __init__(
        self,
        policy: PermissionPolicy,
        approvals: ApprovalManager,
        audit: AuditLog,
    ) -> None:
        self.policy = policy
        self.approvals = approvals
        self.audit = audit

    def issue_approval(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        user_confirmed: bool,
    ):
        """Issue a short-lived grant only after a trusted UI confirms the exact payload."""
        return self.approvals.issue(action, payload, user_confirmed)

    def execute(
        self,
        *,
        action: str,
        permission: str,
        risk_level: str,
        payload: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
        approval_token: str | None = None,
        actor: str = "user",
    ) -> Any:
        """Authorize, audit, then invoke a trusted handler with an unchanged payload."""
        if not callable(handler):
            raise TypeError("A trusted callable handler is required.")
        if not isinstance(payload, dict):
            raise ValueError("Execution payload must be an object.")

        decision = self.policy.decide(
            permission,
            risk_level=risk_level,
            approved=bool(approval_token),
        )
        if not decision.allowed:
            self.audit.record(
                "execution_denied", actor=actor, action=action,
                decision="denied",
                details={"permission": permission, "risk_level": risk_level, "reason": decision.reason},
            )
            raise ExecutionDenied(decision.reason)

        if decision.approval_required:
            if not approval_token or not self.approvals.consume(approval_token, action, payload):
                self.audit.record(
                    "execution_denied", actor=actor, action=action,
                    decision="invalid_or_replayed_approval",
                    details={"permission": permission, "risk_level": risk_level},
                )
                raise ExecutionDenied("A valid, unexpired, action-bound approval is required.")

        self.audit.record(
            "execution_started", actor=actor, action=action, decision="allowed",
            details={"permission": permission, "risk_level": risk_level},
        )
        try:
            result = handler(dict(payload))
        except Exception as exc:
            self.audit.record(
                "execution_failed", actor=actor, action=action, decision="failed",
                details={"error_type": type(exc).__name__, "error": str(exc)[:500]},
            )
            raise
        self.audit.record(
            "execution_completed", actor=actor, action=action, decision="completed",
            details={"result_type": type(result).__name__},
        )
        return result
