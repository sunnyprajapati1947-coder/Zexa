"""Bounded self-repair planning; this module proposes fixes but never applies them."""
from __future__ import annotations

from typing import Any


_REMEDIATIONS = {
    "python_version": {
        "title": "Use a supported Python runtime",
        "reason": "Zexa requires Python 3.11 or newer.",
        "steps": ["Install Python 3.11 or newer from a trusted package source.", "Reinstall Zexa in the intended environment."],
        "risk": "environment_change",
    },
    "project_env_file": {
        "title": "Review local environment configuration",
        "reason": "No .env file was found in the current working directory.",
        "steps": ["Open the Zexa project directory.", "Create a local .env from the documented example, if online features are needed.", "Keep credentials private and never commit .env."],
        "risk": "credential_setup",
    },
    "groq_api_key": {
        "title": "Configure the optional online brain credential",
        "reason": "No Groq API key is configured.",
        "steps": ["If using the online brain, obtain a key from the official provider.", "Set GROQ_API_KEY locally; do not paste it into chat or commit it."],
        "risk": "credential_setup",
    },
    "groq_model": {
        "title": "Choose an available online model",
        "reason": "GROQ_MODEL is not configured.",
        "steps": ["Check the provider's current model catalogue.", "Set GROQ_MODEL to a model ID available to your account."],
        "risk": "configuration_change",
    },
    "local_model_runtime": {
        "title": "Install the optional local inference runtime",
        "reason": "llama-cli was not found.",
        "steps": ["If offline inference is needed, install a trusted ARM64-compatible llama.cpp build.", "Verify llama-cli is on PATH before selecting offline mode."],
        "risk": "package_installation",
    },
    "android_termux": {
        "title": "Run the phone setup from Termux",
        "reason": "The current process does not appear to be running inside Termux.",
        "steps": ["Open the official Termux app.", "Run Zexa commands from the project environment in Termux."],
        "risk": "manual_setup",
    },
    "android_bridge_config": {
        "title": "Configure the optional Android bridge",
        "reason": "No bridge token is configured.",
        "steps": ["Install and open the Zexa companion app from a verified build.", "Enable its Accessibility service only if you intend to use phone control.", "Start the local bridge and copy its token directly into the private local .env file."],
        "risk": "accessibility_permission",
    },
    "command:termux-notification": {
        "title": "Enable Termux notifications",
        "reason": "termux-notification is unavailable.",
        "steps": ["Install the official Termux:API app and matching Termux:API package if notifications are needed.", "Reopen Termux and run zexa doctor again."],
        "risk": "package_installation",
    },
    "command:termux-tts-speak": {
        "title": "Enable optional text-to-speech",
        "reason": "termux-tts-speak is unavailable.",
        "steps": ["Install the official Termux:API app and matching package if speech output is needed.", "Run zexa doctor again."],
        "risk": "package_installation",
    },
    "command:termux-speech-to-text": {
        "title": "Enable optional speech input",
        "reason": "termux-speech-to-text is unavailable.",
        "steps": ["Install the official Termux:API app and matching package if speech input is needed.", "Grant microphone permission only when using voice input.", "Run zexa doctor again."],
        "risk": "permission_or_package",
    },
    "command:termux-torch": {
        "title": "Enable optional flashlight control",
        "reason": "termux-torch is unavailable.",
        "steps": ["Install the official Termux:API app and matching package if flashlight control is needed.", "Run zexa doctor again."],
        "risk": "package_installation",
    },
    "command:llama-cli": {
        "title": "Enable optional local inference",
        "reason": "llama-cli was not found on PATH.",
        "steps": ["Install a trusted ARM64-compatible llama.cpp build if offline inference is needed.", "Verify llama-cli is on PATH."],
        "risk": "package_installation",
    },
}


def build_repair_plan(diagnostics: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic plan from known diagnostic IDs; never run commands."""
    if not isinstance(diagnostics, dict) or not isinstance(diagnostics.get("checks"), list):
        raise ValueError("Diagnostics report must contain a checks list.")
    findings = []
    seen = set()
    for item in diagnostics["checks"]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        status = item.get("status")
        if not isinstance(name, str) or name in seen or status not in {"warning", "error"}:
            continue
        seen.add(name)
        template = _REMEDIATIONS.get(name)
        if template is None:
            continue
        findings.append({
            "check": name,
            "status": status,
            **template,
            "execution": "not_executed",
            "approval_required": True,
        })
    return {
        "mode": "proposal_only",
        "automatic_changes": False,
        "commands_executed": False,
        "files_modified": False,
        "findings": findings,
        "next_step": "Review each proposal. Perform setup manually; a future apply workflow must require fresh, action-bound approval and verified rollback.",
    }
