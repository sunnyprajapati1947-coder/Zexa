"""Shared, typed registry and controller for trusted Human Hand capabilities.

The model may request a capability by name and JSON input. Only application-
registered handlers can execute. Permissions, risk levels, and platform
ownership come from trusted code, never from model output.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import json
import math
import re
from types import MappingProxyType
from typing import Any

from .approvals import ApprovalManager
from .audit import AuditLog
from .gateway import ExecutionGateway
from .policy import PermissionPolicy, RISK_LEVELS


_SCHEMA_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}
_PLATFORMS = {"core", "android", "laptop", "browser", "cloud"}
_NAME = re.compile(r"[a-z][a-z0-9_.:-]{0,119}")


@dataclass(frozen=True)
class CapabilitySpec:
    """Trusted, application-authored contract for one executable capability."""

    name: str
    description: str
    permission: str
    risk_level: str
    platform: str
    input_schema: Mapping[str, str]
    handler: Callable[[dict[str, Any]], dict[str, Any]] = field(repr=False, compare=False)
    output_schema: Mapping[str, str] | None = None
    max_input_chars: int = 16_000
    max_output_chars: int = 32_000

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.fullmatch(self.name):
            raise ValueError("Capability name must be a lowercase registered identifier.")
        if not isinstance(self.description, str) or not self.description.strip() or len(self.description) > 500:
            raise ValueError("Capability description must contain 1–500 characters.")
        if not isinstance(self.permission, str) or not self.permission.strip() or len(self.permission) > 120:
            raise ValueError("Capability permission must contain 1–120 characters.")
        if not isinstance(self.risk_level, str) or self.risk_level not in RISK_LEVELS:
            raise ValueError("Capability risk must be low, medium, high, or critical.")
        if not isinstance(self.platform, str) or self.platform not in _PLATFORMS:
            raise ValueError("Capability platform must be core, android, laptop, browser, or cloud.")
        if not callable(self.handler):
            raise TypeError("Capability handler must be a trusted callable.")
        if type(self.max_input_chars) is not int or not 1 <= self.max_input_chars <= 64_000:
            raise ValueError("max_input_chars must be between 1 and 64000.")
        if type(self.max_output_chars) is not int or not 1 <= self.max_output_chars <= 64_000:
            raise ValueError("max_output_chars must be between 1 and 64000.")

        object.__setattr__(self, "permission", self.permission.strip().lower())
        object.__setattr__(self, "input_schema", self._freeze_schema(self.input_schema, "input_schema"))
        if self.output_schema is not None:
            object.__setattr__(self, "output_schema", self._freeze_schema(self.output_schema, "output_schema"))

    @staticmethod
    def _freeze_schema(schema: Mapping[str, str], label: str) -> Mapping[str, str]:
        if not isinstance(schema, Mapping) or len(schema) > 50:
            raise ValueError(f"{label} must contain at most 50 typed fields.")
        copied = dict(schema)
        if any(
            not isinstance(key, str) or not key.strip() or len(key) > 100
            or not isinstance(value, str) or value not in _SCHEMA_TYPES
            for key, value in copied.items()
        ):
            raise ValueError(f"{label} contains an unsupported field name or type.")
        return MappingProxyType(copied)


class CapabilityController:
    """One execution entry point for phone, laptop, browser, and service adapters."""

    def __init__(
        self,
        policy: PermissionPolicy,
        approvals: ApprovalManager,
        audit: AuditLog,
        capabilities: Mapping[str, CapabilitySpec],
    ) -> None:
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise ValueError("At least one trusted capability must be registered.")
        self._capabilities: dict[str, CapabilitySpec] = {}
        for name, spec in capabilities.items():
            if not isinstance(spec, CapabilitySpec) or name != spec.name:
                raise ValueError("Capability registry keys must match trusted capability names.")
            if name in self._capabilities:
                raise ValueError(f"Duplicate capability: {name}")
            self._capabilities[name] = spec
        self._gateway = ExecutionGateway(
            policy,
            approvals,
            audit,
            capabilities={
                name: (spec.permission, spec.risk_level)
                for name, spec in self._capabilities.items()
            },
        )

    @staticmethod
    def _json_copy(value: dict[str, Any], *, limit: int, label: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object.")
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            if len(encoded) > limit:
                raise ValueError(f"{label} exceeds its configured size limit.")
            copied = json.loads(encoded)
        except (TypeError, ValueError, RecursionError) as exc:
            if isinstance(exc, ValueError) and str(exc).endswith("size limit."):
                raise
            raise ValueError(f"{label} must contain bounded, finite JSON data.") from exc
        return copied

    @staticmethod
    def _validate_schema(
        name: str,
        payload: dict[str, Any],
        schema: Mapping[str, str],
        label: str,
    ) -> None:
        missing = set(schema) - set(payload)
        extra = set(payload) - set(schema)
        if missing:
            raise ValueError(f"{name} {label} is missing fields: " + ", ".join(sorted(missing)))
        if extra:
            raise ValueError(f"{name} {label} has unexpected fields: " + ", ".join(sorted(extra)))
        checks = {
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: type(item) is int,
            "number": lambda item: type(item) in (int, float) and math.isfinite(item),
            "boolean": lambda item: type(item) is bool,
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "null": lambda item: item is None,
        }
        for field_name, expected in schema.items():
            if not checks[expected](payload[field_name]):
                raise ValueError(f"{name} {label} field '{field_name}' must be {expected}.")

    def _spec(self, name: str) -> CapabilitySpec:
        if not isinstance(name, str):
            raise PermissionError("Capability name must be a registered string.")
        spec = self._capabilities.get(name)
        if spec is None:
            raise PermissionError("Capability is not registered or enabled.")
        return spec

    def _input(self, spec: CapabilitySpec, payload: dict[str, Any]) -> dict[str, Any]:
        copied = self._json_copy(payload, limit=spec.max_input_chars, label="Capability input")
        self._validate_schema(spec.name, copied, spec.input_schema, "input")
        return copied

    def issue_approval(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        user_confirmed: bool,
    ):
        """Issue a short-lived, one-use approval bound to the exact validated input."""
        spec = self._spec(name)
        validated = self._input(spec, payload)
        return self._gateway.issue_approval(
            action=spec.name,
            payload=validated,
            user_confirmed=user_confirmed,
        )

    def execute(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        approval_token: str | None = None,
        actor: str = "user",
    ) -> dict[str, Any]:
        """Execute only the handler registered in trusted application code."""
        spec = self._spec(name)
        validated = self._input(spec, payload)

        def invoke(data: dict[str, Any]) -> dict[str, Any]:
            result = spec.handler(data)
            copied = self._json_copy(
                result, limit=spec.max_output_chars, label="Capability output"
            )
            if spec.output_schema is not None:
                self._validate_schema(spec.name, copied, spec.output_schema, "output")
            return copied

        return self._gateway.execute(
            action=spec.name,
            permission=spec.permission,
            risk_level=spec.risk_level,
            payload=validated,
            handler=invoke,
            approval_token=approval_token,
            actor=actor,
        )

    def list_capabilities(self) -> list[dict[str, Any]]:
        """Return safe capability metadata; never expose handler objects or secrets."""
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "permission": spec.permission,
                "risk_level": spec.risk_level,
                "platform": spec.platform,
                "input_schema": dict(spec.input_schema),
                "output_schema": dict(spec.output_schema) if spec.output_schema is not None else None,
            }
            for spec in sorted(self._capabilities.values(), key=lambda item: item.name)
        ]
