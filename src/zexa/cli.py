"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import sys

from .config import get_config, load_env_file
from .groq import chat


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
    args = parser.parse_args()

    load_env_file()
    try:
        config = get_config()
        answer = chat(
            config,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": " ".join(args.prompt)},
            ],
        )
        print(answer)
    except (ValueError, RuntimeError) as exc:
        print(f"zexa: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
