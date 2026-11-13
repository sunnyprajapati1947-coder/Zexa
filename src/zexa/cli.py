"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import json
import sys

from .config import get_config, load_env_file
from .groq import chat
from .planner import create_plan
from .skills import default_registry
from .tools import default_router


SYSTEM_PROMPT = (
    "You are Zexa, a precise, helpful assistant. "
    "You may explain and draft plans, but never claim to have performed an external action. "
    "Consequential actions require explicit user approval through a separate trusted tool."
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="zexa", description="Zexa — Groq-only assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask Zexa a question")
    ask_parser.add_argument("prompt", nargs="+", help="Question or instruction")

    plan_parser = subparsers.add_parser("plan", help="Create a proposed task plan")
    plan_parser.add_argument("goal", nargs="+", help="Goal to break into steps")

    subparsers.add_parser("skills", help="List registered skills")
    subparsers.add_parser("tools", help="List safe local tools")

    args = parser.parse_args()
    registry = default_registry()
    router = default_router()

    if args.command == "skills":
        for skill in registry.list():
            print(f"{skill.name}: {skill.description}")
        return
    if args.command == "tools":
        for tool in router.list():
            print(f"{tool.name}: {tool.description}")
        return

    load_env_file()
    try:
        config = get_config()
        if args.command == "plan":
            print(json.dumps(create_plan(config, registry, " ".join(args.goal)), indent=2))
            print("\nPlan only: no tools or external actions were executed.")
            return
        answer = chat(
            config,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": " ".join(args.prompt)},
            ],
        )
        print(answer)
    except (ValueError, RuntimeError, KeyError, PermissionError) as exc:
        print(f"zexa: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
