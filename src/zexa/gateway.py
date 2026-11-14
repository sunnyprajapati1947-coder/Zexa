"""Guarded synchronous execution gateway for registered Zexa capabilities.

Capability identity, permission, and risk are supplied by trusted application
configuration, never by model output or a caller-selected risk label. Tool
handlers must be trusted callables; models may only request registered names.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from .approvals import ApprovalManager
from .audit import AuditLog
from .policy import PermissionPolicy, RISK_LEVELS


class ExecutionDenied(PermissionError):
    """Raised when policy, capability, or approval checks reject an action."""


class ExecutionGateway:
    def __init__(
        self,
        policy: PermissionPolicy,
        approvals: ApprovalManager,
        audit: AuditLog,
        *,
        capabilities: Mapping[str, tuple[str, str]],
    ) -> None:
        self.policy = policy
        self.approvals = approvals
        self.audit = audit
        self._capabilities: dict[str, tuple[str, str]] = {}
        for action, definition in capabilities.items():
            if (
                not isinstance(action, str) or not action.strip() or len(action) > 120
                or not isinstance(definition, tuple) or len(definition) != 2
            ):
                raise ValueError("Each capability must map an action name to (permission, risk_level).")
            permission, risk_level = definition
            if (
                not isinstance(permission, str) or not permission.strip()
                or risk_level not in RISK_LEVELS
            ):
                raise ValueError("Capability permission or risk level is invalid.")
            self._capabilities[action] = (permission.strip().lower(), risk_level)

    def _capability(self, action: str) -> tuple[str, str]:
        capability = self._capabilities.get(action)
        if capability is None:
            raise ExecutionDenied("Action is not registered as a trusted capability.")
        return capability

    def issue_approval(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        user_confirmed: bool,
    ):
        """Issue a short-lived grant for a registered consequential action."""
        permission, risk_level = self._capability(action)
        decision = self.policy.decide(permission, risk_level=risk_level, approved=True)
        if not decision.allowed or not decision.approval_required:
            raise ExecutionDenied("Approval can only be issued for a granted capability that requires approval.")
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

        try:
            registered_permission, registered_risk = self._capability(action)
            if (
                not isinstance(permission, str)
                or permission.strip().lower() != registered_permission
                or risk_level != registered_risk
            ):
                raise ExecutionDenied("Caller-supplied permission or risk does not match trusted capability metadata.")

            decision = self.policy.decide(
                registered_permission,
                risk_level=registered_risk,
                approved=bool(approval_token),
            )
            if not decision.allowed:
                raise ExecutionDenied(decision.reason)

            if decision.approval_required:
                if not approval_token or not self.approvals.consume(approval_token, action, payload):
                    raise ExecutionDenied("A valid, unexpired, action-bound approval is required.")
        except ExecutionDenied as exc:
            self.audit.record(
                "execution_denied", actor=actor, action=action,
                decision="denied", details={"reason": str(exc)[:300]},
            )
            raise

        self.audit.record(
            "execution_started", actor=actor, action=action, decision="allowed",
            details={"permission": registered_permission, "risk_level": registered_risk},
        )
        try:
            result = handler(dict(payload))
        except Exception as exc:
            # Do not persist exception text: it may contain customer data or secrets.
            self.audit.record(
                "execution_failed", actor=actor, action=action, decision="failed",
                details={"error_type": type(exc).__name__},
            )
            raise
        self.audit.record(
            "execution_completed", actor=actor, action=action, decision="completed",
            details={"result_type": type(result).__name__},
        )
        return result
