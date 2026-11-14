"""Multi-provider brain routing: xAI Grok, Groq, and local llama.cpp/Qwen."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .groq import chat as groq_chat
from .xai import chat as xai_chat


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


class XaiBrain:
    name = "grok-xai"

    def __init__(self, config: dict[str, str], timeout: int | None = None) -> None:
        self.config = dict(config)
        self.timeout = timeout or int(config.get("timeout", "120"))

    def chat(self, messages: Messages) -> str:
        return xai_chat(self.config, messages, timeout=self.timeout)


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
    """On-device llama.cpp adapter; lets GGUF metadata select its chat template."""

    name = "qwen-local"

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
                "Set ZEXA_LOCAL_MODEL to a valid GGUF model path."
            )
        system_text = "\n".join(
            item.get("content", "")
            for item in messages
            if item.get("role") == "system"
        ).strip()
        transcript = "\n".join(
            f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
            for item in messages
            if item.get("role") != "system"
        ).strip()
        if not transcript:
            raise RuntimeError("Local model needs at least one non-system message.")
        command = [
            executable, "-m", str(self.config.model_path),
            "-cnv", "-st", "-p", transcript,
            "-n", str(self.config.max_tokens),
            "-c", str(self.config.context), "-t", str(self.config.threads),
            "--no-display-prompt",
        ]
        if system_text:
            command.extend(["-sys", system_text])
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True,
                timeout=self.config.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Local Qwen model timed out.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "unknown llama.cpp error")[-1200:]
            raise RuntimeError(f"Local Qwen model failed: {detail}") from exc
        answer = (result.stdout or "").strip()
        if not answer:
            raise RuntimeError("Local Qwen model returned an empty response.")
        return answer


class BrainRouter:
    """Route requests to configured providers; fallback only on connectivity errors."""

    MODES = {"auto", "online", "offline", "grok", "groq", "qwen"}

    def __init__(
        self,
        online: Brain | None,
        offline: Brain | None,
        mode: str = "auto",
        fallbacks: list[Brain] | None = None,
    ) -> None:
        if mode not in self.MODES:
            raise ValueError("Brain mode must be auto, online, offline, grok, groq, or qwen.")
        self.online = online
        self.offline = offline
        self.mode = mode
        self.fallbacks = list(fallbacks or [])

    @staticmethod
    def _is_network_failure(error: Exception) -> bool:
        if not isinstance(error, RuntimeError):
            return False
        message = str(error)
        return message.startswith(
            ("Could not reach Groq API:", "Could not reach xAI API:")
        )

    def chat(self, messages: Messages) -> BrainReply:
        if self.mode in {"offline", "qwen"}:
            if self.offline is None:
                raise RuntimeError("Local Qwen brain is not configured.")
            return BrainReply(self.offline.chat(messages), self.offline.name, True)

        if self.mode in {"grok", "groq"}:
            if self.online is None:
                raise RuntimeError(f"The {self.mode} brain is not configured.")
            return BrainReply(self.online.chat(messages), self.online.name, False)

        if self.online is None:
            if self.mode == "online":
                raise RuntimeError("No online brain is configured.")
            if self.offline is None:
                raise RuntimeError("No configured brain is available.")
            return BrainReply(self.offline.chat(messages), self.offline.name, True)

        candidates = [self.online]
        if self.mode == "auto":
            candidates.extend(self.fallbacks)
            if self.offline is not None:
                candidates.append(self.offline)

        last_error: Exception | None = None
        for index, provider in enumerate(candidates):
            try:
                return BrainReply(
                    provider.chat(messages),
                    provider.name,
                    provider is self.offline,
                )
            except Exception as exc:
                last_error = exc
                if self.mode != "auto" or not self._is_network_failure(exc):
                    raise
                if index == len(candidates) - 1:
                    break
        if last_error is not None:
            raise RuntimeError(
                "All configured providers were unreachable."
            ) from last_error
        raise RuntimeError("No configured brain is available.")


def build_brain_router(
    groq_config: dict[str, str] | None,
    mode: str | None = None,
    local_config: LocalModelConfig | None = None,
    xai_config: dict[str, str] | None = None,
) -> BrainRouter:
    """Build the requested provider order without downloading models or keys."""
    selected_mode = (mode or os.getenv("ZEXA_BRAIN_MODE", "auto")).strip().lower()
    if selected_mode not in BrainRouter.MODES:
        raise ValueError(
            "ZEXA_BRAIN_MODE must be auto, online, offline, grok, groq, or qwen."
        )

    grok = XaiBrain(xai_config) if xai_config else None
    groq = GroqBrain(groq_config) if groq_config else None
    local = LocalLlamaBrain(local_config or LocalModelConfig.from_env())
    qwen = local if local.available() else None

    if selected_mode == "grok":
        if grok is None:
            raise RuntimeError("Grok brain is not configured; check XAI_API_KEY.")
        return BrainRouter(grok, qwen, selected_mode)
    if selected_mode == "groq":
        if groq is None:
            raise RuntimeError("Groq brain is not configured; check GROQ_API_KEY and GROQ_MODEL.")
        return BrainRouter(groq, qwen, selected_mode)
    if selected_mode in {"offline", "qwen"}:
        if qwen is None:
            raise RuntimeError(
                "Local Qwen brain is not ready: check llama-cli and ZEXA_LOCAL_MODEL."
            )
        return BrainRouter(None, qwen, selected_mode)
    if selected_mode == "online":
        primary = grok or groq
        if primary is None:
            raise RuntimeError("Online brain is not configured; set XAI_API_KEY or GROQ_API_KEY.")
        return BrainRouter(primary, qwen, selected_mode)

    order = [
        item.strip().lower()
        for item in os.getenv("ZEXA_PROVIDER_ORDER", "grok,groq,qwen").split(",")
        if item.strip()
    ]
    if not order or any(item not in {"grok", "groq", "qwen"} for item in order):
        raise ValueError("ZEXA_PROVIDER_ORDER may contain only grok, groq, and qwen.")
    providers = {"grok": grok, "groq": groq, "qwen": qwen}
    configured: list[Brain] = []
    seen: set[str] = set()
    for item in order:
        provider = providers[item]
        if provider is not None and item not in seen:
            configured.append(provider)
            seen.add(item)
    if not configured:
        raise RuntimeError(
            "No brain is ready. Configure XAI_API_KEY, GROQ_API_KEY, or a local GGUF model."
        )
    primary = configured[0]
    local_fallback = qwen if qwen is not primary and "qwen" not in seen else None
    fallbacks = configured[1:]
    if local_fallback is not None:
        fallbacks.append(local_fallback)
    return BrainRouter(
        primary,
        qwen,
        "auto",
        fallbacks=fallbacks,
    )
