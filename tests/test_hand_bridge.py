import unittest
from unittest.mock import patch

from zexa.hand import AccessibilityBridge


class AccessibilityBridgeApprovalTests(unittest.TestCase):
    def make_bridge(self):
        return AccessibilityBridge("a" * 64)

    def test_perform_waits_for_native_approval_and_returns_result(self):
        bridge = self.make_bridge()
        responses = iter([
            {"status": "pending_approval", "request_id": "request-123"},
            {"status": "pending_approval", "request_id": "request-123"},
            {"status": "completed", "ok": True, "request_id": "request-123"},
        ])
        calls = []
        bridge._request = lambda method, path, payload=None: (
            calls.append((method, path, payload)) or next(responses)
        )
        with patch("zexa.hand.time.sleep") as sleep:
            result = bridge.perform("back", {}, approve=lambda action, payload: True)
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0:2], ("POST", "/v1/action"))
        self.assertEqual(calls[1][0:2], ("GET", "/v1/action/request-123"))
        self.assertEqual(calls[2][0:2], ("GET", "/v1/action/request-123"))
        self.assertEqual(sleep.call_count, 1)

    def test_native_denial_raises_permission_error(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"status": "pending_approval", "request_id": "request-2"}
            if args[0] == "POST"
            else {"status": "denied", "ok": False}
        )
        with self.assertRaises(PermissionError):
            bridge.perform("home", {}, approve=lambda action, payload: True)

    def test_native_expiry_raises_timeout_error(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"status": "pending_approval", "request_id": "request-3"}
            if args[0] == "POST"
            else {"status": "expired_or_unknown", "ok": False}
        )
        with self.assertRaises(TimeoutError):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_invalid_request_id_is_rejected(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {"status": "pending_approval", "request_id": "../bad"}
        with self.assertRaises(RuntimeError):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_client_approval_remains_required(self):
        bridge = self.make_bridge()
        with self.assertRaises(PermissionError):
            bridge.perform("back", {}, approve=None)


if __name__ == "__main__":
    unittest.main()
