"""Visible, user-approved browser navigation for the laptop Human Hand.

This adapter only opens a validated HTTPS URL in the laptop owner's default
browser. It does not read browser profiles, cookies, passwords, page contents,
or automate clicks/forms/submissions.
"""
from __future__ import annotations

import ipaddress
import webbrowser
from urllib.parse import urlsplit


def validate_browser_url(value: str) -> str:
    """Return a normalized public HTTPS URL or reject unsafe/ambiguous targets."""
    if (
        not isinstance(value, str) or not value or len(value) > 2048
        or any(ord(char) <= 32 or ord(char) == 127 for char in value)
    ):
        raise ValueError("Browser URL must be a valid public HTTPS URL.")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Browser URL has an invalid authority or port.") from exc
    if (
        parsed.scheme.lower() != "https" or not parsed.hostname
        or parsed.username is not None or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ValueError("Only public HTTPS URLs on the standard port are supported.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Browser URL hostname is invalid.") from exc
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local") or "." not in host:
        raise ValueError("Local and single-label browser destinations are not supported.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Private, local, and reserved browser destinations are not supported.")
    normalized = parsed._replace(scheme="https", netloc=host, fragment="").geturl()
    if len(normalized) > 2048:
        raise ValueError("Browser URL is too long.")
    return normalized


def open_browser_url(value: str) -> dict[str, object]:
    """Open one validated HTTPS URL in the owner's visible default browser."""
    url = validate_browser_url(value)
    try:
        opened = webbrowser.open(url, new=2, autoraise=True)
    except Exception as exc:
        raise RuntimeError("Could not open the laptop's default browser.") from exc
    if opened is not True:
        raise RuntimeError("The laptop did not report that a browser window was opened.")
    return {"opened": True, "host": urlsplit(url).hostname}
