"""Central deny-by-default permission policy for Zexa tool execution.

This module decides whether a requested capability may run. It does not execute
tools and deliberately does not infer permissions from model-generated text.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


RISK_LEVELS = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    permission: str
    risk_level: str
    approval_required: bool


class PermissionPolicy:
    """Explicit capability allowlist with approval gates for consequential work."""

    def __init__(
        self,
        granted_permissions: Iterable[str] = (),
        *,
        require_approval_for: Iterable[str] = ("high", "critical"),
    ) -> None:
        self._grants = self._normalize(granted_permissions)
        self._approval_risks = self._normalize_risks(require_approval_for)

    @staticmethod
    def _normalize(values: Iterable[str]) -> frozenset[str]:
        result = set()
        for value in values:
            if not isinstance(value, str) or not value.strip() or len(value) > 120:
                raise ValueError("Permissions must be non-empty strings of at most 120 characters.")
            result.add(value.strip().lower())
        return frozenset(result)

    @staticmethod
    def _normalize_risks(values: Iterable[str]) -> frozenset[str]:
        risks = frozenset(values)
        if not risks <= RISK_LEVELS:
            raise ValueError("Unknown risk level in approval policy.")
        return risks

    def decide(
        self,
        permission: str,
        *,
        risk_level: str = "low",
        approved: bool = False,
    ) -> PolicyDecision:
        if not isinstance(permission, str) or not permission.strip() or len(permission) > 120:
            raise ValueError("A valid permission name is required.")
        permission = permission.strip().lower()
        if risk_level not in RISK_LEVELS:
            raise ValueError("risk_level must be low, medium, high, or critical.")

        if permission not in self._grants:
            return PolicyDecision(
                False, "Permission is not explicitly granted.", permission,
                risk_level, risk_level in self._approval_risks,
            )

        approval_required = risk_level in self._approval_risks
        if approval_required and approved is not True:
            return PolicyDecision(
                False, "Fresh user approval is required for this risk level.",
                permission, risk_level, True,
            )

        return PolicyDecision(
            True, "Explicit permission and required approval are present.",
            permission, risk_level, approval_required,
        )

    def grant(self, permission: str) -> None:
        self._grants = self._grants | self._normalize((permission,))

    def revoke(self, permission: str) -> bool:
        normalized = self._normalize((permission,))
        if not normalized <= self._grants:
            return False
        self._grants = self._grants - normalized
        return True

    def list_grants(self) -> tuple[str, ...]:
        return tuple(sorted(self._grants))
