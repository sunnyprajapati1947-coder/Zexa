"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import json
import sys

from .android import AndroidCapabilityProbe, TermuxAndroidHand, TermuxVoice
from .config import get_config, load_env_file
from .groq import chat
from .memory import MemoryStore
from .planner import create_plan
from .skills import default_registry
from .tasks import TaskStore
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
    subparsers.add_parser("android", help="Inspect optional Android/Termux capabilities")
    notify_parser = subparsers.add_parser("notify", help="Send one notification after an explicit CLI request")
    notify_parser.add_argument("title")
    notify_parser.add_argument("message", nargs="+")
    subparsers.add_parser("listen", help="Capture one speech transcript (microphone starts only when invoked)")
    speak_parser = subparsers.add_parser("speak", help="Speak text using Android text-to-speech")
    speak_parser.add_argument("text", nargs="+")

    mem_parser = subparsers.add_parser("memory", help="Manage explicitly saved local memories")
    mem_sub = mem_parser.add_subparsers(dest="memory_command", required=True)
    mem_save = mem_sub.add_parser("save", help="Save or update a memory")
    mem_save.add_argument("key")
    mem_save.add_argument("value", nargs="+")
    mem_get = mem_sub.add_parser("get", help="Recall one memory")
    mem_get.add_argument("key")
    mem_sub.add_parser("list", help="List saved memory keys and values")
    mem_forget = mem_sub.add_parser("forget", help="Delete one memory")
    mem_forget.add_argument("key")
    mem_sub.add_parser("clear", help="Delete all saved memories")

    task_parser = subparsers.add_parser("tasks", help="Manage local task history")
    task_sub = task_parser.add_subparsers(dest="task_command", required=True)
    task_add = task_sub.add_parser("add", help="Record a task")
    task_add.add_argument("title", nargs="+")
    task_list = task_sub.add_parser("list", help="List recent tasks")
    task_list.add_argument("--limit", type=int, default=50)
    task_update = task_sub.add_parser("status", help="Update a task status")
    task_update.add_argument("task_id", type=int)
    task_update.add_argument("status")
    task_update.add_argument("--notes", default=None)

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
    if args.command == "android":
        print(json.dumps(AndroidCapabilityProbe().as_dict(), ensure_ascii=False, indent=2))
        return
    if args.command == "listen":
        try:
            print(TermuxVoice().listen())
        except (RuntimeError, OSError) as exc:
            print(f"zexa: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return
    if args.command == "speak":
        try:
            TermuxVoice().speak(" ".join(args.text))
            print("Speech completed.")
        except (ValueError, RuntimeError, OSError) as exc:
            print(f"zexa: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return
    if args.command == "notify":
        try:
            TermuxAndroidHand().notify(args.title, " ".join(args.message))
            print("Notification sent.")
        except (ValueError, RuntimeError, OSError) as exc:
            print(f"zexa: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        return
    if args.command == "memory":
        store = MemoryStore()
        if args.memory_command == "save":
            print(f"Saved memory ID: {store.remember(args.key, ' '.join(args.value))}")
        elif args.memory_command == "get":
            item = store.recall(args.key)
            print(json.dumps(item, ensure_ascii=False, indent=2) if item else "Memory not found.")
        elif args.memory_command == "list":
            print(json.dumps(store.list_memories(), ensure_ascii=False, indent=2))
        elif args.memory_command == "forget":
            print("Memory deleted." if store.forget(args.key) else "Memory not found.")
        elif args.memory_command == "clear":
            print(f"Deleted {store.clear()} memories.")
        return
    if args.command == "tasks":
        store = TaskStore()
        if args.task_command == "add":
            print(f"Task created: #{store.create(' '.join(args.title))}")
        elif args.task_command == "list":
            print(json.dumps(store.list_tasks(args.limit), ensure_ascii=False, indent=2))
        elif args.task_command == "status":
            changed = store.update_status(args.task_id, args.status, args.notes)
            print("Task updated." if changed else "Task not found.")
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
