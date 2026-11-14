"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

from .android import AndroidCapabilityProbe, TermuxAndroidHand, TermuxVoice
from .agents import AgentOrchestrator
from .config import get_config, load_env_file
from .brain import build_brain_router
from .intent import route_utterance
from .jobs import JobQueue, JobWorker
from .hand import AccessibilityBridge
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



def _explicit_torch_request(transcript: str) -> str | None:
    """Recognize only direct, unambiguous flashlight on/off commands."""
    words = set(re.findall(r"[a-z]+|[\u0900-\u097f]+", transcript.casefold()))
    device_words = {"flash", "flashlight", "torch", "टॉर्च", "फ्लैश"}
    on_words = {"on", "start", "chalu", "chaalu", "jala", "जला", "चालू"}
    off_words = {"off", "stop", "band", "बंद"}
    if not (words & device_words):
        return None
    if words & on_words:
        return "on"
    if words & off_words:
        return "off"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(prog="zexa", description="Zexa — dual-brain phone-first assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask Zexa a question")
    ask_parser.add_argument("prompt", nargs="+", help="Question or instruction")

    plan_parser = subparsers.add_parser("plan", help="Create a proposed task plan")
    plan_parser.add_argument("goal", nargs="+", help="Goal to break into steps")
    agent_parser = subparsers.add_parser("agent", help="Run a bounded multi-agent workflow")
    agent_parser.add_argument("goal", nargs="+", help="Goal for specialist agents")

    skills_parser = subparsers.add_parser("skills", help="List registered skills")
    skills_parser.add_argument("--json", action="store_true", help="Show skill schemas, permissions, risk and budgets")
    subparsers.add_parser("tools", help="List safe local tools")
    subparsers.add_parser("android", help="Inspect optional Android/Termux capabilities")
    notify_parser = subparsers.add_parser("notify", help="Send one notification after an explicit CLI request")
    notify_parser.add_argument("title")
    notify_parser.add_argument("message", nargs="+")
    subparsers.add_parser("listen", help="Capture one speech transcript (microphone starts only when invoked)")
    speak_parser = subparsers.add_parser("speak", help="Speak text using Android text-to-speech")
    speak_parser.add_argument("text", nargs="+")
    subparsers.add_parser("voice", help="Capture one utterance, send it to the selected brain, and speak the reply")
    subparsers.add_parser("converse", help="Start a user-controlled continuous voice conversation")

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

    schedule = subparsers.add_parser("schedule-notification", help="Queue a local Android notification")
    schedule.add_argument("--after-seconds", type=int, default=0)
    schedule.add_argument("title")
    schedule.add_argument("message", nargs="+")

    worker_parser = subparsers.add_parser("worker", help="Run the durable background job worker")
    worker_parser.add_argument("--poll-seconds", type=int, default=5)
    worker_parser.add_argument("--once", action="store_true")
    jobs_parser = subparsers.add_parser("jobs", help="List queued background jobs")
    jobs_parser.add_argument("--limit", type=int, default=50)

    bridge_parser = subparsers.add_parser("bridge", help="Inspect or control the opt-in local Android bridge")
    bridge_sub = bridge_parser.add_subparsers(dest="bridge_command", required=True)
    bridge_sub.add_parser("status", help="Read bridge status")
    bridge_sub.add_parser("screen", help="Read the current accessibility snapshot")
    bridge_action = bridge_sub.add_parser("action", help="Perform one approved Android action")
    bridge_action.add_argument("action", choices=["tap", "swipe", "scroll", "back", "home", "input_text", "launch_app"])
    bridge_action.add_argument("payload", help="Action payload as a JSON object")

    args = parser.parse_args()
    registry = default_registry()
    router = default_router()

    if args.command == "schedule-notification":
        if not 0 <= args.after_seconds <= 31_536_000:
            raise SystemExit("zexa: --after-seconds must be between 0 and 31536000.")
        run_at = datetime.now(timezone.utc) + timedelta(seconds=args.after_seconds)
        job_id = JobQueue().enqueue(
            "notification",
            {"title": args.title, "content": " ".join(args.message)},
            run_at=run_at,
        )
        print(f"Notification job queued: #{job_id}")
        return
    if args.command == "jobs":
        print(json.dumps(JobQueue().list_jobs(args.limit), ensure_ascii=False, indent=2))
        return
    if args.command == "worker":
        if not 1 <= args.poll_seconds <= 300:
            raise SystemExit("zexa: --poll-seconds must be between 1 and 300.")
        queue = JobQueue()
        queue.recover_stale()
        worker = JobWorker(queue, {
            "notification": lambda payload: (
                TermuxAndroidHand().notify(payload["title"], payload["content"])
                or "Notification delivered."
            ),
        })
        if args.once:
            print(worker.run_once())
            return
        print("Zexa background worker started. Press Ctrl+C to stop.")
        try:
            while True:
                if worker.run_once() in {"idle", "pending"}:
                    time.sleep(args.poll_seconds)
        except KeyboardInterrupt:
            print("\nZexa background worker stopped.")
        return

    if args.command == "skills":
        if args.json:
            print(json.dumps(registry.metadata(), ensure_ascii=False, indent=2))
        else:
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
        if args.command == "bridge":
            token = os.getenv("ZEXA_BRIDGE_TOKEN", "").strip()
            base_url = os.getenv("ZEXA_BRIDGE_URL", "http://127.0.0.1:8765").strip()
            bridge = AccessibilityBridge(token, base_url)
            if args.bridge_command == "status":
                result = bridge.status()
            elif args.bridge_command == "screen":
                result = bridge.screen()
            else:
                try:
                    payload = json.loads(args.payload)
                except json.JSONDecodeError as exc:
                    raise ValueError("Bridge action payload must be valid JSON.") from exc
                if not isinstance(payload, dict):
                    raise ValueError("Bridge action payload must be a JSON object.")
                print(f"Requested Android action: {args.action}")
                confirmation = input("Type APPROVE to perform this action: ")
                if confirmation != "APPROVE":
                    print("Android action cancelled.")
                    return
                result = bridge.perform(args.action, payload, approve=lambda *_: True)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        mode = os.getenv("ZEXA_BRAIN_MODE", "auto").strip().lower()
        config = None
        if mode != "offline" and os.getenv("GROQ_API_KEY", "").strip():
            config = get_config()
        elif mode == "online":
            config = get_config()
        brain = build_brain_router(config, mode)
        if args.command == "agent":
            results = AgentOrchestrator(brain, registry).run(" ".join(args.goal))
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        if args.command == "voice":
            voice = TermuxVoice()
            transcript = voice.listen()
            print(f"You: {transcript}")
            answer = brain.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT + " For voice replies, answer naturally and concisely in the user's language."},
                    {"role": "user", "content": transcript},
                ],
            ).text
            print(f"Zexa: {answer}")
            voice.speak(answer[:3000])
            return
        if args.command == "converse":
            voice = TermuxVoice()
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT + " In this ongoing voice conversation, answer naturally and concisely in the user's language."}
            ]
            stop_phrases = {"stop", "exit", "quit", "band karo", "bas karo", "बंद करो", "रुको"}
            print("Zexa continuous voice mode started. Say 'stop' or press Ctrl+C to exit.")
            try:
                empty_transcripts = 0
                while True:
                    try:
                        transcript = voice.listen().strip()
                    except RuntimeError as exc:
                        if "No speech transcript was returned" not in str(exc):
                            raise
                        empty_transcripts += 1
                        if empty_transcripts == 1:
                            print("Zexa: Awaaz clear nahi mili. Dobara boliye.")
                        elif empty_transcripts % 3 == 0:
                            print("Zexa: Main listening mode mein hoon. Jab ready ho, boliye.")
                        # Empty captures do not end a user-started session.
                        # Ctrl+C or a spoken stop phrase remains the exit path.
                        time.sleep(1)
                        continue
                    empty_transcripts = 0
                    print(f"You: {transcript}")
                    if transcript.casefold().strip(" .!?") in stop_phrases:
                        print("Zexa: Voice conversation ended.")
                        break
                    torch_state = _explicit_torch_request(transcript)
                    if torch_state:
                        try:
                            TermuxAndroidHand().set_torch(torch_state)
                            answer = "Flashlight on kar di." if torch_state == "on" else "Flashlight band kar di."
                        except (RuntimeError, OSError, ValueError) as exc:
                            answer = f"Flashlight control available nahi hai: {exc}"
                        print(f"Zexa: {answer}")
                        voice.speak(answer)
                        continue
                    routed = route_utterance(config, messages[1:], transcript, brain=brain)
                    intent = routed["intent"]
                    answer = routed["reply"]
                    if intent == "noise" or not answer:
                        print("Zexa: Speech clear nahi thi; is turn ko skip kar raha hoon.")
                        continue
                    if intent == "task_request":
                        print("Zexa: Task request detected. Abhi koi action execute nahi hua.")
                    print(f"Zexa: {answer}")
                    voice.speak(answer[:3000])
                    messages.append({"role": "user", "content": transcript})
                    messages.append({"role": "assistant", "content": answer})
                    # Keep the system prompt and the latest six exchanges to bound context.
                    messages = [messages[0]] + messages[-12:]
            except KeyboardInterrupt:
                print("\nZexa: Voice conversation ended.")
            return
        if args.command == "plan":
            print(json.dumps(create_plan(config, registry, " ".join(args.goal), brain=brain), indent=2))
            print("\nPlan only: no tools or external actions were executed.")
            return
        answer = brain.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": " ".join(args.prompt)},
            ],
        ).text
        print(answer)
    except (ValueError, RuntimeError, KeyError, PermissionError) as exc:
        print(f"zexa: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
