"""Small approval primitives for future tool execution.

This module deliberately does not execute actions. Tool adapters must request
approval before consequential operations and must not treat model text as consent.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalRequest:
    action: str
    explanation: str
    consequential: bool = True


def requires_approval(request: ApprovalRequest) -> bool:
    """Conservative default: consequential actions always require approval."""
    return request.consequential
