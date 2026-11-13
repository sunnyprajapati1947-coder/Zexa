"""Small, explicit skill registry. Skills describe behavior; they do not execute tools."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    system_instruction: str


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
        try:
            return self._skills[name.strip().lower()]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {name}") from exc

    def list(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda item: item.name)


def default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(Skill(
        "general_assistant",
        "Answer questions and explain concepts.",
        "Answer accurately and clearly. State uncertainty when needed.",
    ))
    registry.register(Skill(
        "text_analysis",
        "Summarize, classify, and analyze user-provided text.",
        "Analyze only the text supplied by the user. Do not invent missing facts.",
    ))
    registry.register(Skill(
        "coding_review",
        "Explain code and suggest review findings without executing it.",
        "Review code defensively. Never claim code was run or modified.",
    ))
    return registry
