"""Zexa command-line interface."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

from .android import AndroidCapabilityProbe, TermuxAndroidHand, TermuxVoice
from .android_capabilities import ANDROID_ACTIONS, ANDROID_GRANTABLE_ACTIONS, build_android_capabilities
from .capabilities import CapabilityController
from .agents import AgentOrchestrator
from .config import get_config, get_groq_config, get_xai_config, load_env_file
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
from .learning import LearningAwareBrain, LearningService, LearningStore
from .laptop_client import LaptopAgentClient
from .laptop_apps import LaptopAppRegistry
from .laptop_hand import MAX_WRITE_CHARS, LaptopWorkspace
from .laptop_server import LaptopAgentServer, certificate_fingerprint, generate_laptop_certificate
from .laptop_pairing import LaptopPairingAuthority, secure_owner_only
from .jobs import JobQueue, JobWorker
from .hand import AccessibilityBridge
from .memory import MemoryStore
from .planner import create_plan
from .research import DuckDuckGoSearch, summarize_research
from .skills import default_registry
from .skillpacks import load_imported_manifest
from .tasks import TaskStore
from .tools import default_router


def _register_approved_learning_skills(registry, knowledge_path=None) -> list[str]:
    """Register reviewed prompt-only skills without overriding built-in handlers."""
    path = Path(
        knowledge_path or (Path.home() / ".zexa" / "knowledge.sqlite3")
    ).expanduser()
    if not path.exists():
        return []
    store = LearningStore(path)
    registered = {skill.name for skill in registry.all()}
    added = []
    for skill in store.approved_skills():
        if skill.name in registered:
            continue
        registry.register(skill)
        registered.add(skill.name)
        added.append(skill.name)
    return added


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
    research_parser = subparsers.add_parser("research", help="Search public web snippets and summarize with source references")
    research_parser.add_argument("--limit", type=int, default=5)
    research_parser.add_argument("query", nargs="+", help="Research question")

    learn_parser = subparsers.add_parser("learn", help="Study web or local text into reviewed knowledge")
    learn_sub = learn_parser.add_subparsers(dest="learn_command", required=True)
    learn_research = learn_sub.add_parser("research", help="Research a topic online and save a draft note")
    learn_research.add_argument("--limit", type=int, default=5)
    learn_research.add_argument("query", nargs="+")
    learn_fetch = learn_sub.add_parser("fetch", help="Fetch one public HTTPS page and summarize it into a draft note")
    learn_fetch.add_argument("url")
    learn_import = learn_sub.add_parser("import", help="Summarize a local UTF-8 text file into a draft note")
    learn_import.add_argument("path")
    learn_list = learn_sub.add_parser("list", help="List knowledge notes")
    learn_list.add_argument("--status", choices=["draft", "approved", "rejected", "archived"])
    learn_list.add_argument("--limit", type=int, default=50)
    learn_show = learn_sub.add_parser("show", help="Show one knowledge note")
    learn_show.add_argument("note_id", type=int)
    learn_search = learn_sub.add_parser("search", help="Search approved knowledge notes")
    learn_search.add_argument("query", nargs="+")
    learn_review = learn_sub.add_parser("review", help="Approve, reject, or archive a knowledge note")
    learn_review.add_argument("note_id", type=int)
    learn_review.add_argument("decision", choices=["approved", "rejected", "archived"])
    learn_skill = learn_sub.add_parser("draft-skill", help="Draft an inert skill from an approved note")
    learn_skill.add_argument("note_id", type=int)
    learn_sub.add_parser("skill-drafts", help="List generated skill drafts")
    learn_skill_review = learn_sub.add_parser("review-skill", help="Review a generated skill contract; approval does not enable execution")
    learn_skill_review.add_argument("draft_id", type=int)
    learn_skill_review.add_argument("decision", choices=["approved", "rejected"])

    laptop_parser = subparsers.add_parser("laptop", help="Pair with and use a scoped laptop Human Hand")
    laptop_sub = laptop_parser.add_subparsers(dest="laptop_command", required=True)
    laptop_cert = laptop_sub.add_parser("certificate", help="Generate a self-signed TLS certificate for the laptop agent")
    laptop_cert.add_argument("--host", required=True, help="Laptop's private LAN IPv4 address")
    laptop_cert.add_argument("--cert", default=str(Path.home() / ".zexa" / "laptop-agent.crt"))
    laptop_cert.add_argument("--key", default=str(Path.home() / ".zexa" / "laptop-agent.key"))
    laptop_serve = laptop_sub.add_parser("serve", help="Run the TLS laptop agent on a private IPv4 address")
    laptop_serve.add_argument("--host", required=True, help="Laptop's private LAN IPv4 address")
    laptop_serve.add_argument("--port", type=int, default=9443)
    laptop_serve.add_argument("--workspace", required=True, help="Existing directory to expose")
    laptop_serve.add_argument("--cert", required=True, help="PEM TLS certificate file")
    laptop_serve.add_argument("--key", required=True, help="PEM TLS private key file")
    laptop_serve.add_argument(
        "--pairings", default=str(Path.home() / ".zexa" / "laptop-pairings.sqlite3"),
        help="Owner-only SQLite file for persistent paired clients and replay protection",
    )
    laptop_serve.add_argument(
        "--allow-write", action="store_true",
        help="Allow paired phones to request workspace writes after exact phone-side confirmation",
    )
    laptop_serve.add_argument(
        "--apps", help="Owner-authored JSON manifest of exact laptop app executables and fixed arguments",
    )
    laptop_serve.add_argument(
        "--allow-app-launch", action="store_true",
        help="Allow paired phones to launch only apps in the supplied owner manifest",
    )
    laptop_serve.add_argument(
        "--allow-browser-open", action="store_true",
        help="Allow paired phones to open exact-confirmed public HTTPS URLs in the visible laptop browser",
    )
    laptop_pair = laptop_sub.add_parser("pair", help="Pair this phone using the code shown by the laptop")
    laptop_pair.add_argument("--host", required=True)
    laptop_pair.add_argument("--port", type=int, default=9443)
    laptop_pair.add_argument("--fingerprint", required=True, help="SHA-256 certificate fingerprint confirmed on the laptop")
    laptop_pair.add_argument("--client-id", default="zexa-phone")
    laptop_list = laptop_sub.add_parser("list", help="List the paired laptop workspace")
    laptop_list.add_argument("--host", required=True)
    laptop_list.add_argument("--port", type=int, default=9443)
    laptop_list.add_argument("--client-id", default="zexa-phone")
    laptop_list.add_argument("--dir", default=".")
    laptop_read = laptop_sub.add_parser("read", help="Read one UTF-8 text file from the paired laptop workspace")
    laptop_read.add_argument("--host", required=True)
    laptop_read.add_argument("--port", type=int, default=9443)
    laptop_read.add_argument("--client-id", default="zexa-phone")
    laptop_read.add_argument("path")
    laptop_write = laptop_sub.add_parser("write", help="Write a local UTF-8 text file to the paired laptop after exact confirmation")
    laptop_write.add_argument("--host", required=True)
    laptop_write.add_argument("--port", type=int, default=9443)
    laptop_write.add_argument("--client-id", default="zexa-phone")
    laptop_write.add_argument("--overwrite", action="store_true")
    laptop_write.add_argument("source")
    laptop_write.add_argument("destination")
    laptop_revoke = laptop_sub.add_parser("revoke", help="Revoke remote pairing and delete the local credential")
    laptop_revoke.add_argument("--host", required=True)
    laptop_revoke.add_argument("--port", type=int, default=9443)
    laptop_revoke.add_argument("--client-id", default="zexa-phone")
    laptop_apps = laptop_sub.add_parser("apps", help="List laptop apps explicitly allowlisted by the owner")
    laptop_apps.add_argument("--host", required=True)
    laptop_apps.add_argument("--port", type=int, default=9443)
    laptop_apps.add_argument("--client-id", default="zexa-phone")
    laptop_launch = laptop_sub.add_parser("launch", help="Launch one owner-allowlisted laptop app after exact confirmation")
    laptop_launch.add_argument("--host", required=True)
    laptop_launch.add_argument("--port", type=int, default=9443)
    laptop_launch.add_argument("--client-id", default="zexa-phone")
    laptop_launch.add_argument("app_id")
    laptop_open_url = laptop_sub.add_parser(
        "open-url", help="Open one public HTTPS URL in the paired laptop's visible browser after exact confirmation",
    )
    laptop_open_url.add_argument("--host", required=True)
    laptop_open_url.add_argument("--port", type=int, default=9443)
    laptop_open_url.add_argument("--client-id", default="zexa-phone")
    laptop_open_url.add_argument("url")
    laptop_clients = laptop_sub.add_parser("clients", help="List paired phones on this laptop")
    laptop_clients.add_argument(
        "--pairings", default=str(Path.home() / ".zexa" / "laptop-pairings.sqlite3"),
    )
    laptop_revoke_client = laptop_sub.add_parser(
        "revoke-client", help="Revoke one paired phone immediately from the laptop owner side",
    )
    laptop_revoke_client.add_argument("client_id")
    laptop_revoke_client.add_argument(
        "--pairings", default=str(Path.home() / ".zexa" / "laptop-pairings.sqlite3"),
    )

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

    api_parser = subparsers.add_parser("api", help="Run the authenticated loopback-only local control API")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8765)

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
    bridge_sub.add_parser("grants", help="List active user-approved navigation task grants")
    bridge_grant_revoke = bridge_sub.add_parser("grant-revoke", help="Revoke one active navigation task grant")
    bridge_grant_revoke.add_argument("grant_id")
    bridge_granted_action = bridge_sub.add_parser(
        "grant-action", help="Run one navigation action inside an existing native task grant"
    )
    bridge_granted_action.add_argument("action", choices=sorted(ANDROID_GRANTABLE_ACTIONS))
    bridge_granted_action.add_argument("task_id")
    bridge_granted_action.add_argument("grant_id")
    bridge_granted_action.add_argument("payload", help="Action payload as a JSON object")
    bridge_action = bridge_sub.add_parser("action", help="Perform one approved Android action")
    bridge_action.add_argument("action", choices=sorted(ANDROID_ACTIONS))
    bridge_action.add_argument("payload", help="Action payload as a JSON object")

    args = parser.parse_args()
    load_env_file(Path(os.getenv("ZEXA_ENV_FILE", str(Path.cwd() / ".env"))))

    if args.command == "laptop":
        if args.laptop_command == "certificate":
            fingerprint = generate_laptop_certificate(args.host, args.cert, args.key)
            print("TLS certificate created.")
            print(f"Certificate: {Path(args.cert).expanduser()}")
            print(f"Private key: {Path(args.key).expanduser()} (owner-only permissions)")
            print(f"SHA-256 fingerprint: {fingerprint}")
            print("Confirm this fingerprint locally on the laptop before entering it on the phone.")
            return
        if args.laptop_command == "serve":
            workspace = LaptopWorkspace(args.workspace)
            if args.allow_app_launch and not args.apps:
                raise ValueError("--allow-app-launch requires an owner-authored --apps manifest.")
            app_registry = LaptopAppRegistry(args.apps) if args.apps else None
            server = LaptopAgentServer(
                args.host, args.port, args.cert, args.key, workspace,
                pairing_path=args.pairings, app_registry=app_registry,
            )
            permissions = ["laptop.workspace.list", "laptop.workspace.read"]
            if args.allow_write:
                permissions.append("laptop.workspace.write")
            if args.allow_app_launch:
                permissions.append("laptop.apps.launch")
            if args.allow_browser_open:
                permissions.append("laptop.browser.open")
            offer = server.begin_pairing(permissions=permissions)
            fingerprint = certificate_fingerprint(args.cert)
            print("Zexa laptop Human Hand server started (TLS 1.2+, private IPv4 only).")
            print(f"Persistent pairing store: {Path(args.pairings).expanduser()} (owner-only permissions)")
            print(f"Address: https://{args.host}:{args.port}")
            print(f"TLS SHA-256 fingerprint: {fingerprint}")
            print(f"One-time pairing code: {offer.pairing_code}")
            print(f"Pairing expires in: {offer.expires_in_seconds} seconds")
            print("Remote permissions: " + ", ".join(offer.permissions))
            if args.allow_write:
                print("Remote workspace writes are enabled; every write must be confirmed on the phone.")
            if args.allow_app_launch:
                print("Remote app launch is enabled only for the owner's fixed allowlist; each launch needs exact phone confirmation.")
            if args.allow_browser_open:
                print("Browser navigation is enabled only for exact-confirmed public HTTPS URLs and opens visibly on this laptop.")
            if not args.allow_write and not args.allow_app_launch and not args.allow_browser_open:
                print("Remote access is read-only: workspace list/read only; no shell or app control.")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nLaptop Human Hand server stopped.")
            finally:
                server.close()
            return
        if args.laptop_command in {"clients", "revoke-client"}:
            authority = LaptopPairingAuthority(storage_path=args.pairings)
            if args.laptop_command == "clients":
                print(json.dumps(authority.list_clients(), ensure_ascii=False, indent=2))
                return
            revoked = authority.revoke_client(args.client_id)
            if revoked:
                audit_path = Path.home() / ".zexa" / "laptop_audit.sqlite3"
                if audit_path.is_symlink():
                    raise PermissionError("Laptop audit database must not be a symbolic link.")
                audit_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                secure_owner_only(audit_path.parent, directory=True)
                audit = AuditLog(audit_path)
                secure_owner_only(audit_path)
                audit.record(
                    "laptop_pairing_revoke", actor="laptop_owner",
                    action="pairing.revoke", decision="revoked",
                    details={"client_id": args.client_id, "source": "local_owner_cli"},
                )
                print(f"Pairing revoked for {args.client_id}; the running laptop server will reject it on the next request.")
            else:
                print(f"No pairing found for {args.client_id}.")
            return
        if args.laptop_command == "pair":
            code = getpass.getpass("Enter the 12-digit pairing code shown locally on the laptop: ")
            client = LaptopAgentClient(
                args.host, args.port, args.fingerprint, args.client_id,
            )
            result = client.pair(code)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print("Pairing key stored in the private local Zexa credential file.")
            return
        client = LaptopAgentClient(
            args.host, args.port, None, args.client_id,
        )
        if args.laptop_command == "apps":
            print(json.dumps(client.list_apps(), ensure_ascii=False, indent=2))
        elif args.laptop_command == "list":
            print(json.dumps(client.list_directory(args.dir), ensure_ascii=False, indent=2))
        elif args.laptop_command == "read":
            print(json.dumps(client.read_text(args.path), ensure_ascii=False, indent=2))
        elif args.laptop_command == "write":
            pairing = client.store.get(client.host, client.port, client.client_id)
            if pairing is None or "laptop.workspace.write" not in pairing["permissions"]:
                raise PermissionError(
                    "This laptop pairing is read-only. Restart the laptop server with --allow-write and pair again."
                )
            source_path = Path(args.source).expanduser()
            if not source_path.is_file():
                raise FileNotFoundError("Local source text file does not exist.")
            with source_path.open("rb") as source_file:
                raw = source_file.read(MAX_WRITE_CHARS * 4 + 1)
            if not raw or len(raw) > MAX_WRITE_CHARS * 4:
                raise ValueError("Local source file must contain 1 byte to 512 KB.")
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("Laptop Human Hand writes UTF-8 text files only.") from exc
            if len(content) > MAX_WRITE_CHARS:
                raise ValueError("Local source file exceeds the 128000-character write limit.")
            phrase = ("OVERWRITE " if args.overwrite else "WRITE ") + args.destination
            print(f"Source: {source_path}")
            print(f"Laptop destination: {args.destination}")
            print(f"Characters: {len(content)}")
            print(f"SHA-256: {hashlib.sha256(raw).hexdigest()}")
            if args.overwrite:
                print("This will replace an existing workspace file.")
            confirmation = input(f"Type exactly '{phrase}' to approve this remote write: ")
            if confirmation != phrase:
                print("Remote write cancelled; no data was sent.")
                return
            result = client.write_text(
                args.destination, content, overwrite=args.overwrite, user_confirmed=True
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.laptop_command == "revoke":
            if client.revoke_pairing():
                print("Remote laptop pairing revoked and local credential deleted.")
            else:
                print("Laptop had no active pairing; local credential deleted.")
        elif args.laptop_command == "launch":
            pairing = client.store.get(client.host, client.port, client.client_id)
            if pairing is None or "laptop.apps.launch" not in pairing["permissions"]:
                raise PermissionError(
                    "This phone pairing lacks laptop app-launch permission. Revoke it, restart the laptop server with --allow-app-launch, and pair again."
                )
            phrase = "LAUNCH " + args.app_id
            print(f"Requested laptop application: {args.app_id}")
            confirmation = input(f"Type exactly '{phrase}' to approve: ")
            if confirmation != phrase:
                print("Laptop app launch cancelled.")
                return
            result = client.launch_app(args.app_id, user_confirmed=True)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.laptop_command == "open-url":
            pairing = client.store.get(client.host, client.port, client.client_id)
            if pairing is None or "laptop.browser.open" not in pairing["permissions"]:
                raise PermissionError(
                    "This phone pairing lacks laptop browser permission. Restart the laptop server with --allow-browser-open and pair again."
                )
            from .laptop_browser import validate_browser_url
            normalized_url = validate_browser_url(args.url)
            phrase = "OPEN URL " + normalized_url
            print(f"Requested visible laptop browser destination: {normalized_url}")
            confirmation = input(f"Type exactly '{phrase}' to approve: ")
            if confirmation != phrase:
                print("Laptop browser navigation cancelled.")
                return
            result = client.open_browser_url(normalized_url, user_confirmed=True)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    registry = default_registry()
    _register_approved_learning_skills(registry)
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
    if args.command == "api":
        from .api import serve
        token = os.getenv("ZEXA_API_TOKEN", "").strip()
        if not token:
            raise SystemExit("zexa: set ZEXA_API_TOKEN to a private random value of at least 32 characters.")
        try:
            serve(args.host, args.port, token, JobQueue())
        except (OSError, ValueError) as exc:
            raise SystemExit(f"zexa: {exc}") from exc
        return
    if args.command == "job":
        queue = JobQueue()
        changed = queue.cancel(args.job_id) if args.job_command == "cancel" else queue.retry(args.job_id)
        action = "cancelled" if args.job_command == "cancel" else "queued for retry"
        print(f"Job #{args.job_id} {action}." if changed else f"Job #{args.job_id} was not changed (check its current status).")
        return
    if args.command == "worker":
        if not 1 <= args.poll_seconds <= 300:
            raise SystemExit("zexa: --poll-seconds must be between 1 and 300.")
        queue = JobQueue()
        queue.recover_stale()
        mode = os.getenv("ZEXA_BRAIN_MODE", "auto").strip().lower()
        config = get_config() if mode in {"online", "groq"} or (
            mode == "auto" and os.getenv("GROQ_API_KEY", "").strip()
        ) else None
        brain = build_brain_router(config, mode)
        explicit_permissions = {
            item.strip().lower()
            for item in os.getenv("ZEXA_SKILL_PERMISSIONS", "").split(",")
            if item.strip()
        }
        policy = PermissionPolicy({
            f"skill.execute:{skill.name}" for skill in registry.list()
        } | explicit_permissions)
        audit_path = Path(
            os.getenv("ZEXA_AUDIT_DB", str(Path.home() / ".zexa" / "audit.sqlite3"))
        ).expanduser()
        gateway = ExecutionGateway(
            policy, ApprovalManager(ttl_seconds=60), AuditLog(audit_path),
            capabilities=skill_capabilities(registry),
        )
        skill_engine = SkillExecutionEngine(
            registry, gateway, brain_skill_handlers(registry, brain),
        )
        def run_background_skill(payload):
            return execute_background_skill(
                skill_engine, registry, payload,
                notify=lambda message: TermuxAndroidHand().notify(
                    "Zexa task completed", message,
                ),
            )
        worker = JobWorker(queue, {
            "notification": lambda payload: (
                TermuxAndroidHand().notify(payload["title"], payload["content"])
                or "Notification delivered."
            ),
            "skill_draft": run_background_skill,
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

    if args.command == "skill" and args.skill_command == "list":
        print(json.dumps(registry.metadata(), ensure_ascii=False, indent=2))
        return
    if args.command == "skillpacks":
        manifest = load_imported_manifest()
        if args.skillpacks_command == "status":
            summary = {
                "imported_count": manifest["imported_count"],
                "enabled_count": manifest["enabled_count"],
                "review_required_count": sum(
                    1 for item in manifest["skills"] if item["review_required"]
                ),
                "source_count": len(manifest.get("sources", [])),
                "execution": "disabled; imported references are not executable",
            }
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            if not 1 <= args.limit <= 500:
                raise SystemExit("zexa: --limit must be between 1 and 500.")
            items = [
                {
                    "name": item["name"],
                    "description": item["description"],
                    "license": item["license"],
                    "review_required": item["review_required"],
                    "enabled": False,
                }
                for item in manifest["skills"][:args.limit]
            ]
            print(json.dumps(items, ensure_ascii=False, indent=2))
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

    try:
        if args.command == "bridge":
            token = os.getenv("ZEXA_BRIDGE_TOKEN", "").strip()
            base_url = os.getenv("ZEXA_BRIDGE_URL", "http://127.0.0.1:8765").strip()
            bridge = AccessibilityBridge(token, base_url)
            if args.bridge_command == "status":
                result = bridge.status()
            elif args.bridge_command == "screen":
                result = bridge.screen()
            elif args.bridge_command == "grants":
                result = {"ok": True, "grants": bridge.task_grants()}
            elif args.bridge_command == "grant-revoke":
                revoked = bridge.revoke_task_grant(args.grant_id)
                result = {"ok": revoked, "status": "revoked" if revoked else "not_found", "grant_id": args.grant_id}
            elif args.bridge_command == "grant-action":
                try:
                    payload = json.loads(args.payload)
                except json.JSONDecodeError as exc:
                    raise ValueError("Bridge action payload must be valid JSON.") from exc
                if not isinstance(payload, dict):
                    raise ValueError("Bridge action payload must be a JSON object.")
                active_grant = next(
                    (
                        item for item in bridge.task_grants()
                        if item["grant_id"] == args.grant_id and item["task_id"] == args.task_id
                    ),
                    None,
                )
                if active_grant is None:
                    raise PermissionError("No active native task grant matches this task ID and grant ID.")
                if args.action not in active_grant["allowed_actions"]:
                    raise PermissionError("This action is outside the selected task grant's approved action set.")
                print(f"Using existing native task grant: {args.task_id}")
                print(f"Requested Android action: {args.action}")
                print("Exact payload:", json.dumps(payload, ensure_ascii=False, sort_keys=True))
                result = bridge.perform_granted(args.action, payload, args.task_id, args.grant_id)
            else:
                try:
                    payload = json.loads(args.payload)
                except json.JSONDecodeError as exc:
                    raise ValueError("Bridge action payload must be valid JSON.") from exc
                if not isinstance(payload, dict):
                    raise ValueError("Bridge action payload must be a JSON object.")
                allowed_actions = {
                    item.strip().lower()
                    for item in os.getenv("ZEXA_ALLOWED_ANDROID_ACTIONS", "").split(",")
                    if item.strip()
                }
                known_actions = set(ANDROID_ACTIONS)
                if not allowed_actions <= known_actions:
                    raise ValueError("ZEXA_ALLOWED_ANDROID_ACTIONS contains an unknown action.")
                action_name = f"android.{args.action}"
                print(f"Requested Android action: {args.action}")
                print("Exact payload:", json.dumps(payload, ensure_ascii=False, sort_keys=True))
                if args.action not in allowed_actions:
                    raise PermissionError(
                        f"{args.action} is not enabled. Add it to ZEXA_ALLOWED_ANDROID_ACTIONS "
                        "only if you want to allow this capability."
                    )
                permission_names = {f"android.{name}" for name in allowed_actions}
                capability_specs = build_android_capabilities(bridge, allowed_actions)
                audit_path = Path(
                    os.getenv("ZEXA_AUDIT_DB", str(Path.home() / ".zexa" / "audit.sqlite3"))
                ).expanduser()
                controller = CapabilityController(
                    PermissionPolicy(permission_names),
                    ApprovalManager(ttl_seconds=60),
                    AuditLog(audit_path),
                    capability_specs,
                )
                confirmation = input("Review the exact action and payload above. Type APPROVE to continue: ")
                if confirmation != "APPROVE":
                    print("Android action cancelled.")
                    return
                approval_payload = {"payload": payload}
                approval = controller.issue_approval(
                    action_name, approval_payload, user_confirmed=True,
                )
                result = controller.execute(
                    action_name,
                    approval_payload,
                    approval_token=approval.token,
                )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

        mode = os.getenv("ZEXA_BRAIN_MODE", "auto").strip().lower()
        groq_config = None
        xai_config = None
        if mode in {"auto", "online"}:
            if os.getenv("GROQ_API_KEY", "").strip():
                groq_config = get_groq_config()
            if os.getenv("XAI_API_KEY", "").strip():
                xai_config = get_xai_config()
        elif mode == "grok" and os.getenv("XAI_API_KEY", "").strip():
            xai_config = get_xai_config()
        elif mode == "groq" and os.getenv("GROQ_API_KEY", "").strip():
            groq_config = get_groq_config()
        brain = build_brain_router(
            groq_config,
            mode,
            xai_config=xai_config,
        )
        knowledge_path = Path.home() / ".zexa" / "knowledge.sqlite3"
        conversation_brain = (
            LearningAwareBrain(brain, LearningStore(knowledge_path))
            if knowledge_path.is_file() else brain
        )
        config = groq_config  # Keep legacy planner/voice call signatures compatible.
        if args.command == "learn":
            store = LearningStore()
            if args.learn_command == "research":
                note_id = LearningService(store, brain).research(" ".join(args.query), args.limit)
                print(f"Research saved as draft knowledge note #{note_id}. Review it with: zexa learn show {note_id}")
            elif args.learn_command == "fetch":
                note_id = LearningService(store, brain).fetch_page(args.url)
                print(f"Public webpage saved as draft knowledge note #{note_id}. Review it with: zexa learn show {note_id}")
            elif args.learn_command == "import":
                note_id = LearningService(store, brain).import_text_file(args.path)
                print(f"Local study notes saved as draft knowledge note #{note_id}.")
            elif args.learn_command == "list":
                print(json.dumps([
                    {
                        "note_id": note.note_id, "title": note.title,
                        "source_type": note.source_type, "source_label": note.source_label,
                        "status": note.status, "updated_at": note.updated_at,
                    }
                    for note in store.list_notes(args.limit, args.status)
                ], ensure_ascii=False, indent=2))
            elif args.learn_command == "show":
                note = store.get_note(args.note_id)
                if note is None:
                    print("Knowledge note not found.")
                else:
                    print(json.dumps({
                        "note_id": note.note_id, "title": note.title, "body": note.body,
                        "sources": list(note.sources), "source_type": note.source_type,
                        "source_label": note.source_label, "content_sha256": note.content_sha256,
                        "status": note.status, "created_at": note.created_at,
                        "updated_at": note.updated_at,
                    }, ensure_ascii=False, indent=2))
            elif args.learn_command == "search":
                print(json.dumps([
                    {"note_id": note.note_id, "title": note.title, "body": note.body}
                    for note in store.search_notes(" ".join(args.query))
                ], ensure_ascii=False, indent=2))
            elif args.learn_command == "review":
                if not store.review_note(args.note_id, args.decision):
                    print("Knowledge note not found.")
                else:
                    print(f"Knowledge note #{args.note_id} marked {args.decision}.")
            elif args.learn_command == "draft-skill":
                draft_id = LearningService(store, brain).draft_skill(args.note_id)
                print(f"Skill contract saved as review-required draft #{draft_id}; it remains non-executable.")
            elif args.learn_command == "skill-drafts":
                print(json.dumps([
                    {
                        "draft_id": item.draft_id, "note_id": item.note_id,
                        "name": item.name, "description": item.description,
                        "risk_level": item.risk_level, "status": item.status,
                    }
                    for item in store.list_skill_drafts()
                ], ensure_ascii=False, indent=2))
            elif args.learn_command == "review-skill":
                if not store.review_skill_draft(args.draft_id, args.decision):
                    print("Skill draft not found.")
                else:
                    print(
                        f"Skill draft #{args.draft_id} marked {args.decision}. "
                        "Approved skills with approved source notes are now available to zexa skill list/run. "
                        "They use a prompt-only brain handler; no learned code, tools, or external actions are activated."
                    )
            return

        if args.command == "skill" and args.skill_command == "run":
            try:
                payload = json.loads(args.payload)
            except json.JSONDecodeError as exc:
                raise ValueError("Skill payload must be valid JSON.") from exc
            if not isinstance(payload, dict):
                raise ValueError("Skill payload must be a JSON object.")
            selected = registry.get(args.name)
            explicit_permissions = {
                item.strip().lower()
                for item in os.getenv("ZEXA_SKILL_PERMISSIONS", "").split(",")
                if item.strip()
            }
            grants = {
                f"skill.execute:{skill.name}"
                for skill in registry.list()
            } | explicit_permissions
            policy = PermissionPolicy(grants)
            audit_path = Path(
                os.getenv("ZEXA_AUDIT_DB", str(Path.home() / ".zexa" / "audit.sqlite3"))
            ).expanduser()
            gateway = ExecutionGateway(
                policy,
                ApprovalManager(ttl_seconds=60),
                AuditLog(audit_path),
                capabilities=skill_capabilities(registry),
            )
            engine = SkillExecutionEngine(
                registry, gateway, brain_skill_handlers(registry, brain),
            )
            approval_token = None
            if selected.risk_level in {"high", "critical"}:
                print(f"Skill: {selected.name} (risk: {selected.risk_level})")
                print("Exact input:", json.dumps(payload, ensure_ascii=False, sort_keys=True))
                confirmation = input("Review the exact input. Type APPROVE to continue: ")
                if confirmation != "APPROVE":
                    print("Skill execution cancelled.")
                    return
                approval_token = engine.issue_approval(
                    selected.name, payload, user_confirmed=True,
                ).token
            result = engine.execute(
                selected.name, payload, approval_token=approval_token,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        if args.command == "research":
            query = " ".join(args.query)
            results = DuckDuckGoSearch().search(query, limit=args.limit)
            print(summarize_research(brain, query, results))
            if results:
                print("\
Sources:")
                for index, item in enumerate(results, start=1):
                    print(f"[{index}] {item.title} — {item.url}")
            return
        if args.command == "agent":
            results = AgentOrchestrator(conversation_brain, registry).run(" ".join(args.goal))
            print(json.dumps(results, ensure_ascii=False, indent=2))
            return
        if args.command == "voice":
            voice = TermuxVoice()
            transcript = voice.listen()
            print(f"You: {transcript}")
            answer = conversation_brain.chat(
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
                        # Voice recognition is not an approval channel. Keep device
                        # actions disabled here until they are routed through the
                        # trusted ExecutionGateway and a separate confirmation flow.
                        answer = (
                            "Flashlight request samajh gaya. Voice mode se phone action "
                            "abhi execute nahi hoga; approved bridge action flow use karein."
                        )
                        print(f"Zexa: {answer}")
                        voice.speak(answer)
                        continue
                    routed = route_utterance(config, messages[1:], transcript, brain=conversation_brain)
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
            print(json.dumps(create_plan(config, registry, " ".join(args.goal), brain=conversation_brain), indent=2))
            print("\nPlan only: no tools or external actions were executed.")
            return
        answer = conversation_brain.chat(
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
