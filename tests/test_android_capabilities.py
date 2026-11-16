import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from zexa.android_capabilities import ANDROID_ACTIONS, build_android_capabilities
from zexa.approvals import ApprovalManager
from zexa.audit import AuditLog
from zexa.capabilities import CapabilityController
from zexa.hand import AccessibilityBridge
from zexa.policy import PermissionPolicy


class AndroidCapabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audit = AuditLog(Path(self.temp.name) / "audit.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_only_explicitly_allowlisted_actions_are_registered(self):
        bridge = Mock(spec=AccessibilityBridge)
        capabilities = build_android_capabilities(bridge, ["back", "tap"])
        self.assertEqual(set(capabilities), {"android.back", "android.tap"})
        self.assertTrue(all(item.platform == "android" for item in capabilities.values()))
        self.assertTrue(all(item.risk_level == "high" for item in capabilities.values()))

    def test_unknown_and_duplicate_actions_are_rejected(self):
        bridge = Mock(spec=AccessibilityBridge)
        with self.assertRaisesRegex(ValueError, "unknown action"):
            build_android_capabilities(bridge, ["run_shell"])
        with self.assertRaisesRegex(ValueError, "duplicates"):
            build_android_capabilities(bridge, ["back", "back"])

    def test_android_action_still_requires_controller_approval(self):
        bridge = Mock(spec=AccessibilityBridge)
        bridge.perform.return_value = {"ok": True, "status": "completed"}
        specs = build_android_capabilities(bridge, ["back"])
        policy = PermissionPolicy({"android.back"})
        controller = CapabilityController(
            policy, ApprovalManager(), self.audit, specs,
        )
        with self.assertRaises(PermissionError):
            controller.execute("android.back", {"payload": {}})
        bridge.perform.assert_not_called()

    def test_approved_action_delegates_to_native_approval_bridge(self):
        bridge = Mock(spec=AccessibilityBridge)
        bridge.perform.return_value = {"ok": True, "status": "completed"}
        specs = build_android_capabilities(bridge, ["back"])
        policy = PermissionPolicy({"android.back"})
        controller = CapabilityController(
            policy, ApprovalManager(), self.audit, specs,
        )
        payload = {"payload": {}}
        approval = controller.issue_approval(
            "android.back", payload, user_confirmed=True,
        )
        result = controller.execute(
            "android.back", payload, approval_token=approval.token,
        )
        self.assertEqual(result, {"ok": True, "status": "completed"})
        bridge.perform.assert_called_once()
        args, kwargs = bridge.perform.call_args
        self.assertEqual(args[0:2], ("back", {}))
        self.assertIs(kwargs["approve"]("back", {}), True)

    def test_all_supported_actions_have_a_trusted_definition(self):
        bridge = Mock(spec=AccessibilityBridge)
        specs = build_android_capabilities(bridge, sorted(ANDROID_ACTIONS))
        self.assertEqual(len(specs), len(ANDROID_ACTIONS))

    def test_action_payloads_are_validated_before_bridge_call(self):
        valid = {
            "tap": {"x": 10.5, "y": 20},
            "swipe": {"x1": 1, "y1": 2, "x2": 3, "y2": 4, "duration_ms": 450},
            "scroll": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
            "back": {},
            "home": {},
            "input_text": {"text": "Hello"},
            "launch_app": {"package_name": "com.example.app"},
            "open_url": {"url": "https://example.com/path?q=1"},
        }
        for action, payload in valid.items():
            with self.subTest(action=action):
                bridge = Mock(spec=AccessibilityBridge)
                bridge.perform.return_value = {"ok": True}
                spec = build_android_capabilities(bridge, [action])[f"android.{action}"]
                spec.handler({"payload": payload})
                bridge.perform.assert_called_once()

    def test_invalid_action_payloads_are_rejected_before_bridge_call(self):
        invalid = [
            ("tap", {"x": True, "y": 10}),
            ("tap", {"x": 1, "y": 2, "extra": "ignored"}),
            ("tap", {"x": float("inf"), "y": 2}),
            ("swipe", {"x1": 1, "y1": 2, "x2": 3, "y2": 4, "duration_ms": True}),
            ("back", {"unexpected": True}),
            ("input_text", {"text": "   "}),
            ("input_text", {"text": "x" * 501}),
            ("launch_app", {"package_name": "../../other"}),
            ("open_url", {"url": "javascript:alert(1)"}),
            ("open_url", {"url": "https://user:pass@example.com"}),
            ("open_url", {"url": "https://exa mple.com"}),
            ("open_url", {"url": "file:///etc/passwd"}),
            ("open_url", {"url": "https://example.com", "extra": True}),
        ]
        for action, payload in invalid:
            with self.subTest(action=action, payload=payload):
                bridge = Mock(spec=AccessibilityBridge)
                spec = build_android_capabilities(bridge, [action])[f"android.{action}"]
                with self.assertRaises(ValueError):
                    spec.handler({"payload": payload})
                bridge.perform.assert_not_called()


if __name__ == "__main__":
    unittest.main()
