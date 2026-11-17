"""Visible, user-approved browser navigation for the laptop Human Hand.

This adapter opens validated HTTPS URLs in the laptop owner's default browser
and separately retrieves bounded public-page text. It never reads browser
profiles, cookies, passwords, or active tabs, and never automates page controls.
"""
from __future__ import annotations

import ipaddress
import webbrowser
from urllib.parse import urlsplit

from .research import fetch_public_page


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
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local") or ("." not in host and ":" not in host):
        raise ValueError("Local and single-label browser destinations are not supported.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        labels = host.split(".")
        if (
            len(host) > 253 or any(
                not label or len(label) > 63 or label.startswith("-")
                or label.endswith("-")
                or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in label)
                for label in labels
            )
        ):
            raise ValueError("Browser URL hostname is invalid.")
    else:
        if not address.is_global:
            raise ValueError("Private, local, and reserved browser destinations are not supported.")
    netloc = f"[{host}]" if ":" in host else host
    normalized = parsed._replace(scheme="https", netloc=netloc).geturl()
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


def read_public_page(value: str) -> dict[str, object]:
    """Fetch bounded public HTTPS page text without browser-profile access or scripts."""
    url = validate_browser_url(value)
    page = fetch_public_page(url)
    if not isinstance(page.text, str) or not page.text.strip() or len(page.text) > 40_000:
        raise RuntimeError("Public page returned no readable text or exceeded the text limit.")
    return {
        "title": page.title[:300],
        "url": page.url,
        "text": page.text[:40_000],
        "content_sha256": page.content_sha256,
        "content_trust": "untrusted_reference",
    }
