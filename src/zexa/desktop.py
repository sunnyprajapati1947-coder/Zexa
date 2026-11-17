"""Approval-gated, cross-platform desktop interaction primitives.

This first laptop Human Hand capability opens a user-supplied web URL through
the operating system's registered browser. It never runs shell commands,
reads screen contents, captures keystrokes, or acts without approval.
"""
from __future__ import annotations

import platform
import webbrowser
from typing import Callable
from urllib.parse import urlsplit


class DesktopHand:
    """Minimal desktop adapter with explicit per-action approval."""

    def __init__(self, opener: Callable[..., bool] | None = None) -> None:
        self._opener = opener or webbrowser.open

    @staticmethod
    def status() -> dict[str, str | bool]:
        """Return basic host information without probing or changing the system."""
        return {
            "platform": platform.system().lower() or "unknown",
            "mode": "approval_gated",
            "open_url_available": True,
            "screen_capture": False,
            "keyboard_monitoring": False,
            "shell_execution": False,
        }

    @staticmethod
    def validate_url(url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("URL must be a string.")
        url = url.strip()
        if not url or len(url) > 2048:
            raise ValueError("URL must contain 1–2048 characters.")
        try:
            parsed = urlsplit(url)
            # Accessing .port also validates malformed/out-of-range ports.
            _ = parsed.port
        except ValueError as exc:
            raise ValueError("URL contains an invalid host or port.") from exc
        if parsed.scheme.lower() not in {"http", "https"}:
            raise ValueError("Only HTTP and HTTPS URLs can be opened.")
        if not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("URL must have a hostname and must not contain credentials.")
        if any(ord(char) < 32 for char in url):
            raise ValueError("URL must not contain control characters.")
        return url

    def open_url(
        self,
        url: str,
        approve: Callable[[str, dict[str, str]], bool] | None = None,
    ) -> dict[str, str | bool]:
        """Open one validated URL only after an explicit approval callback."""
        safe_url = self.validate_url(url)
        request = {"url": safe_url}
        if approve is None or approve("open_url", dict(request)) is not True:
            raise PermissionError("Desktop action was not explicitly approved.")
        opened = self._opener(safe_url, new=2, autoraise=False)
        if opened is not True:
            raise RuntimeError("The registered browser did not confirm that the URL was opened.")
        return {"action": "open_url", "url": safe_url, "opened": True}
