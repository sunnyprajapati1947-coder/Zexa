"""Environment-backed configuration for Zexa."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse


def load_env_file(path: Path | None = None) -> None:
    """Load simple KEY=VALUE lines without overriding existing environment values."""
    env_path = path or Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key.replace("_", "").isalnum() and key not in os.environ:
            os.environ[key] = value


def get_config() -> dict[str, str]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "").strip()
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != "api.groq.com":
        raise ValueError("GROQ_BASE_URL must use the official https://api.groq.com host.")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to your local .env file.")
    if not model:
        raise ValueError("GROQ_MODEL is missing. Set a currently available Groq model ID.")
    return {"api_key": api_key, "model": model, "base_url": base_url}
