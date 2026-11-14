"""Authenticated client for Zexa's opt-in Android Accessibility Bridge.

The Android companion service is a separate app and must be installed and
enabled by the device owner. This module never launches adb, shell commands,
or arbitrary URLs. All gesture/action requests require a caller-supplied
approval callback; screen reads are read-only.
"""
from __future__ import annotations

import json
import re
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ALLOWED_ACTIONS = {"tap", "swipe", "scroll", "back", "home", "input_text", "launch_app"}


class AccessibilityBridge:
    def __init__(
        self,
        token: str,
        base_url: str = "http://127.0.0.1:8765",
        timeout: int = 8,
    ) -> None:
        if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~-]{16,256}", token):
            raise ValueError("Bridge token must be 16–256 URL-safe characters.")
        parsed = urlparse(base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Accessibility bridge must use local HTTP loopback only.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Bridge URL must not contain credentials, query, or fragment.")
        if parsed.port != 8765 or parsed.path not in {"", "/"}:
            raise ValueError("Bridge URL must use port 8765 and have no path.")
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = max(1, min(int(timeout), 20))

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=body,
            headers={
                "Authorization": "Bearer " + self.token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method,
        )
        try:
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=self.timeout) as response:
                raw = response.read(256_001)
                if len(raw) > 256_000:
                    raise RuntimeError("Accessibility bridge response exceeded the size limit.")
                result = json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Accessibility bridge returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise RuntimeError("Accessibility bridge is not reachable on this device.") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("Accessibility bridge returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Accessibility bridge response must be a JSON object.")
        return result

    def status(self) -> dict:
        """Read bridge status; does not perform a device action."""
        return self._request("GET", "/v1/status")

    def screen(self) -> dict:
        """Read the current UI accessibility snapshot."""
        return self._request("GET", "/v1/screen")

    def perform(
        self,
        action: str,
        payload: dict,
        approve: Callable[[str, dict], bool] | None = None,
    ) -> dict:
        """Perform one allowlisted action only after an external approval callback."""
        if action not in _ALLOWED_ACTIONS:
            raise ValueError("Action is not allowlisted.")
        if not isinstance(payload, dict):
            raise ValueError("Action payload must be an object.")
        if approve is None or approve(action, dict(payload)) is not True:
            raise PermissionError("Android action was not explicitly approved.")
        return self._request("POST", "/v1/action", {"action": action, "payload": payload})
