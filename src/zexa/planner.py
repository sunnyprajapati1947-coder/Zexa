"""Groq-backed task decomposition. Plans are proposals, never executed here."""
from __future__ import annotations

import json

from .groq import chat
from .skills import SkillRegistry


def create_plan(config: dict[str, str] | None, registry: SkillRegistry, goal: str, brain=None) -> list[dict[str, str]]:
    goal = goal.strip()
    if not goal:
        raise ValueError("A non-empty goal is required.")
    available = [{"name": s.name, "description": s.description} for s in registry.list()]
    messages = [
        {
            "role": "system",
            "content": (
                "Create a concise task plan. Return ONLY valid JSON with this shape: "
                '{"steps":[{"skill":"one allowed skill name","task":"short task"}]}. '
                "Use 1 to 6 steps. Do not include shell commands, tool calls, or claim execution. "
                "Only use skill names from the supplied allowlist."
            ),
        },
        {
            "role": "user",
            "content": json.dumps({"goal": goal, "allowed_skills": available}, ensure_ascii=False),
        },
    ]
    raw = brain.chat(messages).text if brain is not None else chat(config, messages)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Planner response was not valid JSON; no plan was accepted.") from exc
    steps = payload.get("steps") if isinstance(payload, dict) else None
    if not isinstance(steps, list) or not 1 <= len(steps) <= 6:
        raise RuntimeError("Planner returned an invalid number of steps.")
    validated: list[dict[str, str]] = []
    allowed = {skill.name for skill in registry.list()}
    for step in steps:
        if not isinstance(step, dict):
            raise RuntimeError("Planner returned a malformed step.")
        name, task = step.get("skill"), step.get("task")
        if not isinstance(name, str) or name not in allowed:
            raise RuntimeError("Planner selected a skill that is not registered.")
        if not isinstance(task, str) or not task.strip() or len(task) > 500:
            raise RuntimeError("Planner returned an invalid task description.")
        validated.append({"skill": name, "task": task.strip()})
    return validated
