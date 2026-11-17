"""Trusted Android capability definitions for the shared Human Hand controller."""
from __future__ import annotations

from collections.abc import Iterable
import math
import re
from urllib.parse import urlsplit
from typing import Any

from .capabilities import CapabilitySpec
from .hand import AccessibilityBridge


ANDROID_ACTIONS = frozenset({
    "tap", "swipe", "scroll", "back", "home", "input_text", "launch_app", "open_url",
})
ANDROID_GRANTABLE_ACTIONS = frozenset({"swipe", "scroll", "back", "home", "launch_app"})
_PACKAGE_NAME = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+")
_COORDINATE_LIMIT = 10_000.0


def _validate_action_payload(action: str, payload: dict[str, Any]) -> None:
    """Validate the exact Android action contract before it reaches the bridge."""
    if not isinstance(payload, dict):
        raise ValueError("Android action payload must be an object.")

    contracts = {
        "tap": ({"x", "y"}, set()),
        "swipe": ({"x1", "y1", "x2", "y2"}, {"duration_ms"}),
        "scroll": ({"x1", "y1", "x2", "y2"}, {"duration_ms"}),
        "back": (set(), set()),
        "home": (set(), set()),
        "input_text": ({"text"}, set()),
        "launch_app": ({"package_name"}, set()),
        "open_url": ({"url"}, set()),
    }
    required, optional = contracts[action]
    keys = set(payload)
    if not required <= keys or keys - required - optional:
        raise ValueError(f"Invalid fields for Android {action} action.")

    coordinate_fields = {
        "tap": ("x", "y"),
        "swipe": ("x1", "y1", "x2", "y2"),
        "scroll": ("x1", "y1", "x2", "y2"),
    }.get(action, ())
    for field in coordinate_fields:
        value = payload[field]
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= value <= _COORDINATE_LIMIT
        ):
            raise ValueError(f"Android {action} coordinate '{field}' must be a finite number from 0 to 10000.")

    if "duration_ms" in payload:
        duration = payload["duration_ms"]
        if type(duration) is not int or not 100 <= duration <= 2_000:
            raise ValueError("Android gesture duration_ms must be an integer from 100 to 2000.")

    if action == "input_text":
        value = payload["text"]
        if not isinstance(value, str) or not value.strip() or len(value) > 500:
            raise ValueError("Android input_text requires 1–500 non-empty characters.")

    if action == "launch_app":
        value = payload["package_name"]
        if not isinstance(value, str) or not _PACKAGE_NAME.fullmatch(value):
            raise ValueError("Android launch_app requires a valid package name.")

    if action == "open_url":
        value = payload["url"]
        if not isinstance(value, str) or not value or len(value) > 2_048:
            raise ValueError("Android open_url requires a URL of at most 2048 characters.")
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Android open_url does not allow whitespace or control characters.")
        try:
            parsed = urlsplit(value)
            valid = (
                parsed.scheme.lower() in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and (parsed.port is None or 1 <= parsed.port <= 65_535)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Android open_url requires a valid HTTP(S) URL without embedded credentials.")


def build_android_capabilities(
    bridge: AccessibilityBridge,
    allowed_actions: Iterable[str],
) -> dict[str, CapabilitySpec]:
    """Build only explicitly enabled Android actions; native approval stays mandatory."""
    if not callable(getattr(bridge, "perform", None)):
        raise TypeError("A configured Android bridge with a perform() method is required.")
    actions = tuple(allowed_actions)
    if any(not isinstance(action, str) or action not in ANDROID_ACTIONS for action in actions):
        raise ValueError("Android capability list contains an unknown action.")
    if len(actions) != len(set(actions)):
        raise ValueError("Android capability actions must not contain duplicates.")

    capabilities: dict[str, CapabilitySpec] = {}
    for action in actions:
        name = f"android.{action}"

        def handler(data, selected_action=action):
            # Validate nested fields as well as the outer typed controller contract.
            action_payload = data["payload"]
            _validate_action_payload(selected_action, action_payload)
            # The CLI/controller approval is an additional gate. AccessibilityBridge
            # still waits for the Android app's own exact-action confirmation.
            return bridge.perform(
                selected_action,
                action_payload,
                approve=lambda *_: True,
            )

        capabilities[name] = CapabilitySpec(
            name=name,
            description=f"Perform the allowlisted Android {action} action.",
            permission=name,
            risk_level="high",
            platform="android",
            input_schema={"payload": "object"},
            handler=handler,
        )
    return capabilities
