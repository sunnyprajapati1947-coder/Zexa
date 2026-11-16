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
            {"ok": True, "status": "executing", "request_id": "request-123"},
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

    def test_audited_expiry_status_raises_timeout_error(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "request-expired"}
            if args[0] == "POST"
            else {"ok": False, "status": "expired", "request_id": "request-expired"}
        )
        with self.assertRaisesRegex(TimeoutError, "approval expired"):
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
        with self.assertRaisesRegex(RuntimeError, "without confirming success"):
            bridge.perform("back", {}, approve=lambda action, payload: True)

    def test_dispatched_gesture_result_is_returned_without_claiming_completion(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: (
            {"ok": True, "status": "pending_approval", "request_id": "gesture-1"}
            if args[0] == "POST"
            else {"ok": True, "status": "dispatched", "request_id": "gesture-1"}
        )
        with patch("zexa.hand.time.sleep"):
            result = bridge.perform("swipe", {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                                    approve=lambda action, payload: True)
        self.assertEqual(result["status"], "dispatched")
        self.assertTrue(result["ok"])

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

    def test_task_grants_are_listed_only_from_valid_native_response(self):
        bridge = self.make_bridge()
        bridge._request = lambda method, path, payload=None: {
            "ok": True, "grants": [{
                "grant_id": "grant-1",
                "task_id": "research-1",
                "allowed_actions": ["scroll", "back"],
                "expires_at_epoch_ms": 200_000,
                "remaining_actions": 3,
            }]
        }
        self.assertEqual(bridge.task_grants()[0]["grant_id"], "grant-1")

    def test_invalid_task_grant_list_is_rejected(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {"ok": False, "grants": []}
        with self.assertRaises(RuntimeError):
            bridge.task_grants()

    def test_task_grant_list_rejects_unapproved_action_names(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": True,
            "grants": [{
                "grant_id": "grant-1",
                "task_id": "research-1",
                "allowed_actions": ["tap"],
                "expires_at_epoch_ms": 200_000,
                "remaining_actions": 3,
            }],
        }
        with self.assertRaises(RuntimeError):
            bridge.task_grants()

    def test_task_grant_can_be_revoked_through_authenticated_bridge(self):
        bridge = self.make_bridge()
        calls = []
        bridge._request = lambda method, path, payload=None: (
            calls.append((method, path, payload)) or {
                "ok": True, "status": "revoked", "grant_id": "grant-123"
            }
        )
        self.assertTrue(bridge.revoke_task_grant("grant-123"))
        self.assertEqual(calls[0], ("POST", "/v1/grants/revoke", {"grant_id": "grant-123"}))

    def test_task_grant_revoke_reports_missing_and_rejects_invalid_ids(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": False, "status": "not_found", "grant_id": "grant-123"
        }
        self.assertFalse(bridge.revoke_task_grant("grant-123"))
        with self.assertRaises(ValueError):
            bridge.revoke_task_grant("../bad")

    def test_perform_granted_accepts_only_success_for_same_grant(self):
        bridge = self.make_bridge()
        calls = []
        bridge._request = lambda method, path, payload=None: (
            calls.append((method, path, payload)) or {
                "ok": True, "status": "completed", "grant_id": "grant-123", "remaining_actions": 4
            }
        )
        result = bridge.perform_granted("scroll", {"x": 10, "y": 20, "direction": "down", "duration_ms": 500},
                                        "research-1", "grant-123")
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][1], "/v1/action")
        self.assertEqual(calls[0][2]["task_id"], "research-1")
        self.assertEqual(calls[0][2]["grant_id"], "grant-123")

    def test_perform_granted_surfaces_unknown_execution_without_retry(self):
        bridge = self.make_bridge()
        calls = []
        bridge._request = lambda *args, **kwargs: (
            calls.append(args) or {
                "ok": False, "status": "execution_unknown", "grant_id": "grant-123",
                "error": "Do not retry automatically.",
            }
        )
        with self.assertRaisesRegex(TimeoutError, "Do not retry automatically"):
            bridge.perform_granted("scroll", {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                                   "research-1", "grant-123")
        self.assertEqual(len(calls), 1)

    def test_perform_granted_accepts_dispatched_gesture_result(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": True, "status": "dispatched", "grant_id": "grant-123", "remaining_actions": 3
        }
        result = bridge.perform_granted("scroll", {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                                        "research-1", "grant-123")
        self.assertEqual(result["status"], "dispatched")
        self.assertTrue(result["ok"])

    def test_task_grant_cannot_run_taps_or_text_entry(self):
        bridge = self.make_bridge()
        for action, payload in [
            ("tap", {"x": 1, "y": 1}),
            ("input_text", {"text": "hello"}),
        ]:
            with self.subTest(action=action), self.assertRaises(ValueError):
                bridge.perform_granted(action, payload, "research-1", "grant-123")

    def test_task_grant_rejects_url_navigation(self):
        bridge = self.make_bridge()
        with self.assertRaises(ValueError):
            bridge.perform_granted(
                "open_url", {"url": "https://example.com/path"}, "research-1", "grant-123"
            )

    def test_task_grant_rejects_invalid_ids(self):
        bridge = self.make_bridge()
        with self.assertRaises(ValueError):
            bridge.perform_granted("back", {}, "../bad", "grant-123")
        with self.assertRaises(ValueError):
            bridge.perform_granted("back", {}, "research-1", "../bad")

    def test_task_grant_scope_mismatch_is_permission_error(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": False, "status": "grant_scope_mismatch_or_expired"
        }
        with self.assertRaises(PermissionError):
            bridge.perform_granted("back", {}, "research-1", "grant-123")

    def test_task_grant_does_not_accept_unverified_completion(self):
        bridge = self.make_bridge()
        bridge._request = lambda *args, **kwargs: {
            "ok": True, "status": "completed", "grant_id": "different-grant"
        }
        with self.assertRaisesRegex(RuntimeError, "different task grant"):
            bridge.perform_granted("back", {}, "research-1", "grant-123")


if __name__ == "__main__":
    unittest.main()
