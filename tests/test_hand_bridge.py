import unittest
from unittest.mock import patch

from zexa.hand import AccessibilityBridge


class AccessibilityBridgeApprovalTests(unittest.TestCase):
    def make_bridge(self):
        return AccessibilityBridge("a" * 64)

    def test_perform_waits_for_native_approval_and_returns_result(self):
        bridge = self.make_bridge()
        responses = iter([
            {"ok": True, "status": "pending_approval", "request_id": "request-123"},
            {"ok": True, "status": "pending_approval", "request_id": "request-123"},
            {"ok": True, "status": "completed", "request_id": "request-123"},
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
            {"ok": True, "status": "pending_approval", "request_id": "request-2"}
            if args[0] == "POST"
            else {"ok": False, "status": "denied", "request_id": "request-2"}
        )
        with self.assertRaises(PermissionError):
            bridge.perform("home", {}, approve=lambda action, payload: True)

    def test_native_expiry_raises_timeout_error(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-3"}
            if args[0] == "POST"
            else {"ok": True, "status": "expired_or_unknown", "request_id": "request-3"}
        )
        with self.assertRaises(TimeoutError):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_native_failure_is_not_reported_as_success(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-4"}
            if args[0] == "POST"
            else {"ok": False, "status": "failed", "request_id": "request-4"}
        )
        with self.assertRaisesRegex(RuntimeError, "action failed"):
            bridge.perform("tap", {"x": 10, "y": 10}, approve=lambda action, payload: True)

    def test_enqueue_response_cannot_claim_action_completed(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": True, "status": "completed", "request_id": "request-5"
        }
        with self.assertRaisesRegex(RuntimeError, "native approval request"):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_completed_result_must_confirm_success(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-6"}
            if args[0] == "POST"
            else {"ok": False, "status": "completed", "request_id": "request-6"}
        )
        with self.assertRaisesRegex(RuntimeError, "without a successful"):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_result_must_match_the_queued_request_id(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-7"}
            if args[0] == "POST"
            else {"ok": True, "status": "completed", "request_id": "different-request"}
        )
        with self.assertRaisesRegex(RuntimeError, "different approval request"):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_invalid_request_id_is_rejected(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": True, "status": "pending_approval", "request_id": "../bad"
        }
        with self.assertRaises(RuntimeError):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_pending_status_must_be_explicitly_successful(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-8"}
            if args[0] == "POST"
            else {"ok": False, "status": "pending_approval", "request_id": "request-8"}
        )
        with self.assertRaisesRegex(RuntimeError, "invalid approval status"):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_client_approval_remains_required(self):
        bridge = self.make_bridge()
        with self.assertRaises(PermissionError):
            bridge.perform("back", {}, approve=None)


if __name__ == "__main__":
    unittest.main()
