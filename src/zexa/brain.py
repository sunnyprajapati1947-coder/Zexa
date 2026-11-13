"""Dual-brain routing: Groq online plus an optional local llama.cpp model.

The router never downloads models or silently changes providers. In auto mode it
uses Groq first and falls back locally only for a network-connectivity failure.
Authentication, quota, model, and server errors remain visible to the caller.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .groq import chat as groq_chat


Messages = list[dict[str, str]]


class Brain(Protocol):
    name: str

    def chat(self, messages: Messages) -> str: ...


@dataclass(frozen=True)
class BrainReply:
    text: str
    brain: str
    offline: bool


class GroqBrain:
    name = "groq-online"

    def __init__(self, config: dict[str, str], timeout: int = 45) -> None:
        self.config = dict(config)
        self.timeout = timeout

    def chat(self, messages: Messages) -> str:
        return groq_chat(self.config, messages, timeout=self.timeout)


@dataclass(frozen=True)
class LocalModelConfig:
    model_path: Path
    executable: str = "llama-cli"
    threads: int = 4
    context: int = 2048
    max_tokens: int = 512
    timeout: int = 120

    @classmethod
    def from_env(cls) -> "LocalModelConfig":
        return cls(
            model_path=Path(os.getenv("ZEXA_LOCAL_MODEL", "models/local-model.gguf")).expanduser(),
            executable=os.getenv("ZEXA_LLAMA_CLI", "llama-cli"),
            threads=max(1, min(int(os.getenv("ZEXA_LOCAL_THREADS", "4")), 8)),
            context=max(512, min(int(os.getenv("ZEXA_LOCAL_CONTEXT", "2048")), 8192)),
            max_tokens=max(64, min(int(os.getenv("ZEXA_LOCAL_MAX_TOKENS", "512")), 2048)),
            timeout=max(10, min(int(os.getenv("ZEXA_LOCAL_TIMEOUT", "120")), 600)),
        )


class LocalLlamaBrain:
    """On-device llama.cpp adapter; invokes a fixed executable without a shell."""

    name = "llama.cpp-local"

    def __init__(self, config: LocalModelConfig) -> None:
        self.config = config

    def available(self) -> bool:
        return (
            self.config.model_path.is_file()
            and shutil.which(self.config.executable) is not None
        )

    def chat(self, messages: Messages) -> str:
        executable = shutil.which(self.config.executable)
        if not executable:
            raise RuntimeError(
                f"Local runtime '{self.config.executable}' was not found. "
                "Install/build llama.cpp and make llama-cli available in PATH."
            )
        if not self.config.model_path.is_file():
            raise RuntimeError(
                f"Local model file not found: {self.config.model_path}. "
                "Set ZEXA_LOCAL_MODEL to a downloaded GGUF model path."
            )
        # Messages are serialized as plain role-labelled context. This is a
        # conservative generic prompt; model-specific chat templates can be
        # added by a dedicated adapter later.
        prompt = "\n".join(
            f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
            for item in messages
        ) + "\nASSISTANT:"
        command = [
            executable, "-m", str(self.config.model_path),
            "-p", prompt, "-n", str(self.config.max_tokens),
            "-c", str(self.config.context), "-t", str(self.config.threads),
            "--no-display-prompt",
        ]
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True,
                timeout=self.config.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Local model timed out.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "unknown llama.cpp error")[-1200:]
            raise RuntimeError(f"Local model failed: {detail}") from exc
        answer = (result.stdout or "").strip()
        if not answer:
            raise RuntimeError("Local model returned an empty response.")
        return answer


class BrainRouter:
    """Select online/offline brain with explicit, bounded fallback behaviour."""

    MODES = {"auto", "online", "offline"}

    def __init__(
        self,
        online: Brain | None,
        offline: Brain | None,
        mode: str = "auto",
    ) -> None:
        if mode not in self.MODES:
            raise ValueError("Brain mode must be auto, online, or offline.")
        self.online = online
        self.offline = offline
        self.mode = mode

    @staticmethod
    def _is_network_failure(error: Exception) -> bool:
        return isinstance(error, RuntimeError) and str(error).startswith(
            "Could not reach Groq API:"
        )

    def chat(self, messages: Messages) -> BrainReply:
        if self.mode == "offline":
            if self.offline is None:
                raise RuntimeError("Offline brain is not configured.")
            return BrainReply(self.offline.chat(messages), self.offline.name, True)

        if self.online is None:
            if self.mode == "online":
                raise RuntimeError("Online Groq brain is not configured.")
            if self.offline is None:
                raise RuntimeError("Neither online nor offline brain is configured.")
            return BrainReply(self.offline.chat(messages), self.offline.name, True)

        try:
            return BrainReply(self.online.chat(messages), self.online.name, False)
        except Exception as exc:
            if self.mode != "auto" or not self._is_network_failure(exc):
                raise
            if self.offline is None:
                raise RuntimeError(
                    "Groq is unreachable and no offline brain is configured."
                ) from exc
            return BrainReply(self.offline.chat(messages), self.offline.name, True)


def build_brain_router(
    groq_config: dict[str, str] | None,
    mode: str | None = None,
    local_config: LocalModelConfig | None = None,
) -> BrainRouter:
    """Build configured providers; missing credentials do not block offline mode."""
    selected_mode = (mode or os.getenv("ZEXA_BRAIN_MODE", "auto")).strip().lower()
    if selected_mode not in BrainRouter.MODES:
        raise ValueError("ZEXA_BRAIN_MODE must be auto, online, or offline.")
    online = GroqBrain(groq_config) if groq_config else None
    local = LocalLlamaBrain(local_config or LocalModelConfig.from_env())
    offline = local if local.available() else None
    if selected_mode == "offline" and offline is None:
        raise RuntimeError(
            "Offline brain is not ready: check llama-cli and ZEXA_LOCAL_MODEL."
        )
    return BrainRouter(online, offline, selected_mode)
