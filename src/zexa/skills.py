"""Typed skill contracts and an explicit registry.

Skills are declarative capabilities. Registering a skill never grants a tool,
network, filesystem, or Android permission by itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import math


RISK_LEVELS = {"low", "medium", "high", "critical"}
SCHEMA_TYPES = {"string", "integer", "number", "boolean", "object", "array", "null"}


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    system_instruction: str
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    required_permissions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    timeout_seconds: int = 30
    resource_budget: dict[str, int] = field(default_factory=dict)
    risk_level: str = "low"
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip() or len(self.name) > 80:
            raise ValueError("Skill name must contain 1–80 characters.")
        if not self.description.strip() or len(self.description) > 500:
            raise ValueError("Skill description must contain 1–500 characters.")
        if not self.system_instruction.strip() or len(self.system_instruction) > 4000:
            raise ValueError("Skill instruction must contain 1–4000 characters.")
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level must be one of: {', '.join(sorted(RISK_LEVELS))}.")
        if not 1 <= self.timeout_seconds <= 600:
            raise ValueError("Skill timeout must be between 1 and 600 seconds.")
        for schema_name, schema in (
            ("input_schema", self.input_schema),
            ("output_schema", self.output_schema),
        ):
            if not isinstance(schema, dict) or len(schema) > 50:
                raise ValueError(f"{schema_name} must be an object with at most 50 fields.")
            if any(
                not isinstance(key, str) or not key.strip()
                or not isinstance(value, str) or value not in SCHEMA_TYPES
                for key, value in schema.items()
            ):
                raise ValueError(
                    f"{schema_name} must map field names to supported types: "
                    + ", ".join(sorted(SCHEMA_TYPES))
                )
        for field_name, values in (
            ("required_permissions", self.required_permissions),
            ("dependencies", self.dependencies),
        ):
            if len(values) > 30 or any(
                not isinstance(value, str) or not value.strip() or len(value) > 100
                for value in values
            ):
                raise ValueError(f"{field_name} contains an invalid entry.")
        if len(self.resource_budget) > 20 or any(
            not isinstance(key, str) or not key.strip()
            or type(value) is not int or not 1 <= value <= 1_000_000
            for key, value in self.resource_budget.items()
        ):
            raise ValueError("resource_budget values must be bounded positive integers.")


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        key = skill.name.strip().lower()
        if not key or not key.replace("_", "").isalnum():
            raise ValueError("Skill names may contain only letters, numbers, and underscores.")
        if key in self._skills:
            raise ValueError(f"Skill already registered: {key}")
        self._skills[key] = skill

    def get(self, name: str) -> Skill:
        key = name.strip().lower()
        skill = self._skills.get(key)
        if skill is None:
            raise KeyError(f"Unknown skill: {name}")
        if not skill.enabled:
            raise KeyError(f"Skill is disabled: {name}")
        return skill

    def list(self) -> list[Skill]:
        """Return enabled skills only, suitable for planners and agents."""
        return sorted(
            (skill for skill in self._skills.values() if skill.enabled),
            key=lambda item: item.name,
        )

    def all(self) -> list[Skill]:
        """Return enabled and disabled skill definitions for administration."""
        return sorted(self._skills.values(), key=lambda item: item.name)

    def set_enabled(self, name: str, enabled: bool) -> bool:
        key = name.strip().lower()
        skill = self._skills.get(key)
        if skill is None:
            return False
        self._skills[key] = replace(skill, enabled=bool(enabled))
        return True

    def validate_payload(self, name: str, payload: dict, output: bool = False) -> dict:
        """Validate a skill input/output object against its declared type contract."""
        skill = self.get(name)
        if not isinstance(payload, dict):
            raise ValueError("Skill payload must be a JSON object.")
        schema = skill.output_schema if output else skill.input_schema
        missing = set(schema) - set(payload)
        extra = set(payload) - set(schema)
        if missing:
            raise ValueError("Missing skill fields: " + ", ".join(sorted(missing)))
        if extra:
            raise ValueError("Unexpected skill fields: " + ", ".join(sorted(extra)))
        checkers = {
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: type(item) is int,
            "number": lambda item: type(item) in (int, float) and math.isfinite(item),
            "boolean": lambda item: type(item) is bool,
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "null": lambda item: item is None,
        }
        for field_name, expected in schema.items():
            if not checkers[expected](payload[field_name]):
                raise ValueError(f"Skill field '{field_name}' must be {expected}.")
        try:
            encoded = json.dumps(payload, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("Skill payload must contain JSON-compatible values.") from exc
        max_chars = skill.resource_budget.get("max_input_chars", 20000)
        if not output and len(encoded) > max_chars:
            raise ValueError("Skill input exceeds its configured character budget.")
        return dict(payload)

    def metadata(self) -> list[dict]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": dict(skill.input_schema),
                "output_schema": dict(skill.output_schema),
                "required_permissions": list(skill.required_permissions),
                "dependencies": list(skill.dependencies),
                "timeout_seconds": skill.timeout_seconds,
                "resource_budget": dict(skill.resource_budget),
                "risk_level": skill.risk_level,
                "enabled": skill.enabled,
            }
            for skill in self.all()
        ]


def default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(Skill(
        "general_assistant",
        "Answer questions and explain concepts.",
        "Answer accurately and clearly. State uncertainty when needed.",
        input_schema={"prompt": "string"},
        output_schema={"answer": "string"},
        timeout_seconds=45,
        resource_budget={"max_input_chars": 12000, "max_output_tokens": 2048},
    ))
    registry.register(Skill(
        "text_analysis",
        "Summarize, classify, and analyze user-provided text.",
        "Analyze only the text supplied by the user. Do not invent missing facts.",
        input_schema={"text": "string", "operation": "string"},
        output_schema={"analysis": "string"},
        timeout_seconds=60,
        resource_budget={"max_input_chars": 20000, "max_output_tokens": 3000},
    ))
    registry.register(Skill(
        "coding_review",
        "Explain code and suggest review findings without executing it.",
        "Review code defensively. Never claim code was run or modified.",
        input_schema={"code": "string", "focus": "string"},
        output_schema={"findings": "string"},
        required_permissions=(),
        timeout_seconds=90,
        resource_budget={"max_input_chars": 24000, "max_output_tokens": 3500},
        risk_level="medium",
    ))
    registry.register(Skill(
        "customer_support_drafter",
        "Draft customer support replies using only supplied customer context and approved policies.",
        "Draft a courteous support reply. Use only the policy supplied by the user. "
        "Never promise refunds, credits, delivery dates, or exceptions unless the policy explicitly authorizes them. "
        "Do not send the reply; label it as a draft for human review.",
        input_schema={"customer_message": "string", "approved_policy": "string"},
        output_schema={"reply_draft": "string", "assumptions": "string"},
        timeout_seconds=60,
        resource_budget={"max_input_chars": 12000, "max_output_tokens": 1800},
        risk_level="medium",
    ))
    registry.register(Skill(
        "proposal_writer",
        "Draft a service proposal from user-provided scope, timeline, and pricing.",
        "Write a clear service proposal using only supplied facts. Do not invent prices, "
        "client details, deliverables, deadlines, guarantees, or legal terms. Mark missing "
        "details as placeholders. This is a draft and must not be sent automatically.",
        input_schema={"service": "string", "client_needs": "string", "scope_timeline_pricing": "string"},
        output_schema={"proposal_draft": "string", "missing_details": "string"},
        timeout_seconds=90,
        resource_budget={"max_input_chars": 16000, "max_output_tokens": 3000},
        risk_level="low",
    ))
    registry.register(Skill(
        "invoice_drafter",
        "Format an invoice draft from user-supplied billing details and amounts.",
        "Format an invoice draft using only the supplied seller, client, line items, dates, "
        "and amounts. Do not invent tax rules, bank details, invoice numbers, or payment status. "
        "Do not initiate payment or claim the invoice was issued. Flag missing information.",
        input_schema={"seller_client_details": "string", "line_items_and_amounts": "string", "dates": "string"},
        output_schema={"invoice_draft": "string", "missing_details": "string"},
        timeout_seconds=60,
        resource_budget={"max_input_chars": 12000, "max_output_tokens": 2200},
        risk_level="medium",
    ))
    registry.register(Skill(
        "faq_builder",
        "Create frequently asked questions from approved product or service material.",
        "Create questions and answers only from the supplied source material. If an answer "
        "is not supported, mark it as requiring confirmation instead of guessing.",
        input_schema={"approved_source_material": "string"},
        output_schema={"faq": "string", "unanswered_questions": "string"},
        timeout_seconds=60,
        resource_budget={"max_input_chars": 20000, "max_output_tokens": 2500},
        risk_level="low",
    ))
    return registry
