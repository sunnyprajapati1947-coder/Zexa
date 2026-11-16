"""Trusted Android capability definitions for the shared Human Hand controller."""
from __future__ import annotations

from collections.abc import Iterable

from .capabilities import CapabilitySpec
from .hand import AccessibilityBridge


ANDROID_ACTIONS = frozenset({
    "tap", "swipe", "scroll", "back", "home", "input_text", "launch_app",
})


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
            # The CLI/controller approval is an additional gate. AccessibilityBridge
            # still waits for the Android app's own exact-action confirmation.
            return bridge.perform(
                selected_action,
                data["payload"],
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
