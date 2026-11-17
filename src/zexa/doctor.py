"""Read-only environment diagnostics; never executes commands or changes files."""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def run_diagnostics(which=shutil.which, environ=None, cwd=None) -> dict:
    """Return redacted setup checks without exposing secrets or performing actions."""
    env = os.environ if environ is None else environ
    root = Path.cwd() if cwd is None else Path(cwd)

    python_ok = sys.version_info >= (3, 11)
    termux = bool(env.get("PREFIX", "").startswith("/data/data/com.termux"))
    command_names = (
        "termux-notification",
        "termux-tts-speak",
        "termux-speech-to-text",
        "termux-torch",
        "llama-cli",
    )
    commands = {name: bool(which(name)) for name in command_names}
    checks = [
        {
            "name": "python_version",
            "status": "ok" if python_ok else "error",
            "detail": platform.python_version(),
            "required": True,
        },
        {
            "name": "project_env_file",
            "status": "ok" if (root / ".env").is_file() else "warning",
            "detail": "present" if (root / ".env").is_file() else "not found in current directory",
            "required": False,
        },
        {
            "name": "groq_api_key",
            "status": "ok" if env.get("GROQ_API_KEY", "").strip() else "warning",
            "detail": "configured" if env.get("GROQ_API_KEY", "").strip() else "not configured",
            "required": False,
        },
        {
            "name": "groq_model",
            "status": "ok" if env.get("GROQ_MODEL", "").strip() else "warning",
            "detail": "configured" if env.get("GROQ_MODEL", "").strip() else "not configured",
            "required": False,
        },
        {
            "name": "local_model_runtime",
            "status": "ok" if commands["llama-cli"] else "info",
            "detail": "llama-cli available" if commands["llama-cli"] else "optional llama-cli not found",
            "required": False,
        },
        {
            "name": "android_termux",
            "status": "ok" if termux else "info",
            "detail": "Termux environment detected" if termux else "not running inside Termux",
            "required": False,
        },
        {
            "name": "android_bridge_config",
            "status": "ok" if env.get("ZEXA_BRIDGE_TOKEN", "").strip() else "info",
            "detail": "bridge token configured" if env.get("ZEXA_BRIDGE_TOKEN", "").strip() else "bridge not configured (optional)",
            "required": False,
        },
    ]
    checks.extend(
        {
            "name": f"command:{name}",
            "status": "ok" if available else "info",
            "detail": "available" if available else "not installed (optional)",
            "required": False,
        }
        for name, available in commands.items()
    )
    return {
        "mode": "read_only",
        "actions_executed": False,
        "secrets_exposed": False,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "summary": {
            "total": len(checks),
            "ok": sum(item["status"] == "ok" for item in checks),
            "warnings": sum(item["status"] == "warning" for item in checks),
            "errors": sum(item["status"] == "error" for item in checks),
        },
        "checks": checks,
        "repair": {
            "automatic_changes": False,
            "approval_required_for_changes": True,
            "message": "Diagnostics only. No files, settings, packages, or accounts were changed.",
        },
    }
