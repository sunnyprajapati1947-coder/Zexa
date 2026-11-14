"""Small stdlib-only client for the xAI Responses API."""
from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _extract_text(result: dict) -> str:
    """Extract visible assistant text without exposing encrypted reasoning items."""
    direct = result.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    output = result.get("output", [])
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            if item.get("role") != "assistant":
                continue
            content = item.get("content", [])
            if not isinstance(content, list):
                continue
            for part in content:
                if (
                    isinstance(part, dict)
                    and part.get("type") == "output_text"
                    and isinstance(part.get("text"), str)
                ):
                    chunks.append(part["text"])
    answer = "".join(chunks).strip()
    if not answer:
        raise RuntimeError("xAI returned no visible assistant text.")
    return answer


def chat(
    config: dict[str, str],
    messages: list[dict[str, str]],
    timeout: int | None = None,
) -> str:
    """Send one stateless turn using the recommended Responses API."""
    url = config["base_url"].rstrip("/") + "/responses"
    payload = {
        "model": config["model"],
        "input": messages,
        "store": False,
        "temperature": 0.7,
        "top_p": 0.95,
        "max_output_tokens": int(config.get("max_output_tokens", "1024")),
        "reasoning": {"effort": config.get("reasoning_effort", "low")},
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + config["api_key"],
            "Content-Type": "application/json",
            "User-Agent": "Zexa/0.1.0",
        },
        method="POST",
    )
    request_timeout = timeout or int(config.get("timeout", "120"))
    try:
        with urlopen(request, timeout=request_timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"xAI API returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", None) or str(exc)
        raise RuntimeError(f"Could not reach xAI API: {reason}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("xAI returned an invalid JSON response.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("xAI returned an unexpected Responses API payload.")
    return _extract_text(result)
