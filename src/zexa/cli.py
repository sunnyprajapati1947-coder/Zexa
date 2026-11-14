"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .android import AndroidCapabilityProbe, TermuxAndroidHand, TermuxVoice
from .agents import AgentOrchestrator
from .config import get_groq_config, get_xai_config, load_env_file
from .approvals import ApprovalManager
from .audit import AuditLog
from .gateway import ExecutionGateway
from .policy import PermissionPolicy
from .execution import (
    SkillExecutionEngine, brain_skill_handlers, skill_capabilities,
    execute_background_skill,
)
from .brain import build_brain_router
from .intent import route_utterance
from .jobs import JobQueue, JobWorker
from .hand import AccessibilityBridge
from .memory import MemoryStore
from .planner import create_plan
from .research import DuckDuckGoSearch, summarize_research
from .skills import default_registry
from .skillpacks import load_imported_manifest
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
    parser = argparse.ArgumentParser(prog="zexa", description="Zexa — multi-brain phone-first assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Ask Zexa a question")
    ask_parser.add_argument("prompt", nargs="+", help="Question or instruction")

    plan_parser = subparsers.add_parser("plan", help="Create a proposed task plan")
    plan_parser.add_argument("goal", nargs="+", help="Goal to break into steps")
    agent_parser = subparsers.add_parser("agent", help="Run a bounded multi-agent workflow")
    agent_parser.add_argument("goal", nargs="+", help="Goal for specialist agents")
    research_parser = subparsers.add_parser("research", help="Search public web snippets and summarize with source references")
    research_parser.add_argument("--limit", type=int, default=5)
    research_parser.add_argument("query", nargs="+", help="Research question")

    skill_parser = subparsers.add_parser("skill", help="Run one registered skill through the execution gateway")
    skill_sub = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_sub.add_parser("list", help="List available skill contracts")
    skill_run = skill_sub.add_parser("run", help="Run one skill with a JSON input object")
    skill_run.add_argument("name")
    skill_run.add_argument("payload", help="Input JSON object matching the skill schema")

    skillpacks_parser = subparsers.add_parser("skillpacks", help="Inspect disabled imported skill references")
    skillpacks_sub = skillpacks_parser.add_subparsers(dest="skillpacks_command", required=True)
    skillpacks_sub.add_parser("status", help="Show imported skill pack counts and review status")
    skillpacks_list = skillpacks_sub.add_parser("list", help="List imported skill metadata; imported content stays disabled")
    skillpacks_list.add_argument("--limit", type=int, default=50)

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

    skill_schedule = subparsers.add_parser("schedule-skill", help="Queue a low-risk skill for background processing")
    skill_schedule.add_argument("name")
    skill_schedule.add_argument("payload", help="Input JSON object matching the skill schema")

    schedule = subparsers.add_parser("schedule-notification", help="Queue a local Android notification")
    schedule.add_argument("--after-seconds", type=int, default=0)
    schedule.add_argument("title")
    schedule.add_argument("message", nargs="+")

    worker_parser = subparsers.add_parser("worker", help="Run the durable background job worker")
    worker_parser.add_argument("--poll-seconds", type=int, default=5)
    worker_parser.add_argument("--once", action="store_true")
    jobs_parser = subparsers.add_parser("jobs", help="List queued background jobs")
    jobs_parser.add_argument("--limit", type=int, default=50)
    job_parser = subparsers.add_parser("job", help="Control one queued background job")
    job_sub = job_parser.add_subparsers(dest="job_command", required=True)
    job_cancel = job_sub.add_parser("cancel", help="Cancel a pending job")
    job_cancel.add_argument("job_id", type=int)
    job_retry = job_sub.add_parser("retry", help="Retry a failed job")
    job_retry.add_argument("job_id", type=int)

    bridge_parser = subparsers.add_parser("bridge", help="Inspect or control the opt-in local Android bridge")
    bridge_sub = bridge_parser.add_subparsers(dest="bridge_command", required=True)
    bridge_sub.add_parser("status", help="Read bridge status")
    bridge_sub.add_parser("screen", help="Read the current accessibility snapshot")
    bridge_action = bridge_sub.add_parser("action", help="Perform one approved Android action")
    bridge_action.add_argument("action", choices=["tap", "swipe", "scroll", "back", "home", "input_text", "launch_app"])
    bridge_action.add_argument("payload", help="Action payload as a JSON object")

    args = parser.parse_args()
    load_env_file(Path(os.getenv("ZEXA_ENV_FILE", str(Path.cwd() / ".env"))))
    registry = default_registry()
    router = default_router()

    if args.command == "schedule-skill":
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            raise SystemExit("zexa: skill payload must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise SystemExit("zexa: skill payload must be a JSON object.")
        selected = registry.get(args.name)
        if selected.risk_level != "low":
            raise SystemExit(
                "zexa: only low-risk skills can be queued. Run higher-risk skills interactively for fresh approval."
            )
        registry.validate_payload(selected.name, payload)
        job_id = JobQueue().enqueue(
            "skill_draft", {"name": selected.name, "input": payload},
        )
        print(f"Background skill job queued: #{job_id}")
        return
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
    if args.command == "job":
        queue = JobQueue()
        changed = queue.cancel(args.job_id) if args.job_command == "cancel" else queue.retry(args.job_id)
        print("Updated." if changed else "No matching job could be changed.")
        return
    if args.command == "worker":
        worker = JobWorker()
        if args.once:
            print("Processed." if worker.run_once() else "No due jobs.")
        else:
            worker.run_forever(poll_seconds=args.poll_seconds)
        return
    if args.command == "skillpacks":
        manifest = load_imported_manifest()
        if args.skillpacks_command == "status":
            print(json.dumps({
                "total": len(manifest),
                "enabled": sum(1 for item in manifest if item.get("enabled") is True),
                "disabled": sum(1 for item in manifest if item.get("enabled") is not True),
            }, indent=2))
        else:
            print(json.dumps(manifest[:max(0, args.limit)], ensure_ascii=False, indent=2))
        return
    if args.command == "skills":
        items = registry.list()
        if args.json:
            print(json.dumps([
                {
                    "name": item.name, "description": item.description,
                    "input_schema": item.input_schema, "output_schema": item.output_schema,
                    "permissions": list(item.required_permissions),
                    "dependencies": list(item.dependencies), "timeout_seconds": item.timeout_seconds,
                    "resource_budget": item.resource_budget, "risk_level": item.risk_level,
                    "enabled": item.enabled,
                }
                for item in items
            ], ensure_ascii=False, indent=2))
        else:
            for item in items:
                print(f"{item.name} [{item.risk_level}] — {item.description}")
        return
    if args.command == "tools":
        print(json.dumps(router.describe(), ensure_ascii=False, indent=2))
        return
    if args.command == "android":
        print(json.dumps(AndroidCapabilityProbe().report(), ensure_ascii=False, indent=2))
        return
    if args.command == "notify":
        TermuxAndroidHand().notify(args.title, " ".join(args.message))
        print("Notification sent.")
        return
    if args.command == "listen":
        print(TermuxVoice().listen_once())
        return
    if args.command == "speak":
        TermuxVoice().speak(" ".join(args.text))
        return
    if args.command == "bridge":
        bridge = AccessibilityBridge(
            os.getenv("ZEXA_BRIDGE_TOKEN", ""),
            os.getenv("ZEXA_BRIDGE_URL", "http://127.0.0.1:8765"),
        )
        if args.bridge_command == "status":
            print(json.dumps(bridge.status(), ensure_ascii=False, indent=2))
            return
        if args.bridge_command == "screen":
            print(json.dumps(bridge.screen(), ensure_ascii=False, indent=2))
            return
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Bridge payload must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Bridge payload must be a JSON object.")
        allowed_actions = {
            item.strip().lower()
            for item in os.getenv("ZEXA_ALLOWED_ANDROID_ACTIONS", "").split(",")
            if item.strip()
        }
        known_actions = {"tap", "swipe", "scroll", "back", "home", "input_text", "launch_app"}
        if not allowed_actions <= known_actions:
            raise ValueError("ZEXA_ALLOWED_ANDROID_ACTIONS contains an unknown action.")
        permission_names = {f"android.{name}" for name in allowed_actions}
        capabilities = {
            f"android.{name}": (f"android.{name}", "high")
            for name in allowed_actions
        }
        audit_path = Path(
            os.getenv("ZEXA_AUDIT_DB", str(Path.home() / ".zexa" / "audit.sqlite3"))
        ).expanduser()
        gateway = ExecutionGateway(
            PermissionPolicy(permission_names),
            ApprovalManager(ttl_seconds=60),
            AuditLog(audit_path),
            capabilities=capabilities,
        )
        action_name = f"android.{args.action}"
        print(f"Requested Android action: {args.action}")
        print("Exact payload:", json.dumps(payload, ensure_ascii=False, sort_keys=True))
        if args.action not in allowed_actions:
            raise PermissionError(
                f"{args.action} is not enabled. Add it to ZEXA_ALLOWED_ANDROID_ACTIONS "
                "only if you want to allow this capability."
            )
        confirmation = input("Review the exact action and payload above. Type APPROVE to continue: ")
        if confirmation != "APPROVE":
            print("Android action cancelled.")
            return
        approval = gateway.issue_approval(
            action=action_name, payload=payload, user_confirmed=True,
        )
        result = gateway.execute(
            action=action_name,
            permission=action_name,
            risk_level="high",
            payload=payload,
            approval_token=approval.token,
            handler=lambda approved_payload: bridge.perform(
                args.action, approved_payload, approve=lambda *_: True,
            ),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    mode = os.getenv("ZEXA_BRAIN_MODE", "auto").strip().lower()
    groq_config = (
        get_groq_config() if os.getenv("GROQ_API_KEY", "").strip() else None
    )
    xai_config = (
        get_xai_config() if os.getenv("XAI_API_KEY", "").strip() else None
    )
    brain = build_brain_router(
        groq_config,
        mode,
        xai_config=xai_config,
    )
    if args.command == "ask":
        from .brain import BrainReply
        answer = brain.chat([{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": " ".join(args.prompt)}])
        print(answer.text)
        print(f"\n[brain: {answer.brain}]")
        return
    if args.command == "plan":
        result = create_plan(None, registry, " ".join(args.goal), brain=brain)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "agent":
        result = AgentOrchestrator(registry, brain).run(" ".join(args.goal))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "research":
        search = DuckDuckGoSearch()
        items = search.search(" ".join(args.query), limit=args.limit)
        result = summarize_research(brain, " ".join(args.query), items)
        print(result)
        return
    if args.command == "voice":
        transcript = TermuxVoice().listen_once()
        result = route_utterance(None, [], transcript, brain=brain)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("reply"):
            TermuxVoice().speak(result["reply"])
        return
    if args.command == "converse":
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
        voice = TermuxVoice()
        while True:
            try:
                transcript = voice.listen_once()
            except KeyboardInterrupt:
                break
            if transcript.strip().lower() in {"exit", "quit", "stop"}:
                break
            history.append({"role": "user", "content": transcript})
            answer = brain.chat(history)
            history.append({"role": "assistant", "content": answer.text})
            print(answer.text)
            voice.speak(answer.text)


if __name__ == "__main__":
    main()
