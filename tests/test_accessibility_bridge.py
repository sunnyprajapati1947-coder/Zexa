import unittest
from unittest.mock import patch

from zexa.hand import AccessibilityBridge


TOKEN = "a" * 64


class AccessibilityBridgeTests(unittest.TestCase):
    def test_only_loopback_http_on_expected_port_is_accepted(self):
        for url in (
            "https://127.0.0.1:8765",
            "http://example.com:8765",
            "http://192.168.1.10:8765",
            "http://127.0.0.1:8080",
            "http://user@127.0.0.1:8765",
            "http://127.0.0.1:8765/path",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                AccessibilityBridge(TOKEN, base_url=url)

    def test_token_must_be_url_safe_and_bounded(self):
        for token in ("short", "x" * 257, "bad token " + "x" * 20):
            with self.subTest(token=token), self.assertRaises(ValueError):
                AccessibilityBridge(token)

    def test_timeout_is_bounded(self):
        self.assertEqual(AccessibilityBridge(TOKEN, timeout=0).timeout, 1)
        self.assertEqual(AccessibilityBridge(TOKEN, timeout=99).timeout, 20)

    def test_status_and_screen_are_read_only_requests(self):
        bridge = AccessibilityBridge(TOKEN)
        with patch.object(bridge, "_request", side_effect=[{"ok": True}, {"nodes": []}]) as request:
            self.assertEqual(bridge.status(), {"ok": True})
            self.assertEqual(bridge.screen(), {"nodes": []})
        self.assertEqual(request.call_args_list[0].args, ("GET", "/v1/status"))
        self.assertEqual(request.call_args_list[1].args, ("GET", "/v1/screen"))

    def test_action_is_not_sent_without_explicit_true_approval(self):
        bridge = AccessibilityBridge(TOKEN)
        with patch.object(bridge, "_request") as request:
            with self.assertRaises(PermissionError):
                bridge.perform("back", {}, approve=None)
            with self.assertRaises(PermissionError):
                bridge.perform("back", {}, approve=lambda action, payload: 1)
        request.assert_not_called()

    def test_action_requires_allowlist_and_object_payload(self):
        bridge = AccessibilityBridge(TOKEN)
        with patch.object(bridge, "_request") as request:
            with self.assertRaises(ValueError):
                bridge.perform("shell", {}, approve=lambda *_: True)
            with self.assertRaises(ValueError):
                bridge.perform("back", [], approve=lambda *_: True)
        request.assert_not_called()

    def test_approved_action_posts_only_the_requested_action_and_payload(self):
        bridge = AccessibilityBridge(TOKEN)
        payload = {"x": 20, "y": 30}
        with patch.object(bridge, "_request", return_value={"ok": True}) as request:
            result = bridge.perform("tap", payload, approve=lambda action, data: action == "tap" and data == payload)
        self.assertEqual(result, {"ok": True})
        request.assert_called_once_with("POST", "/v1/action", {"action": "tap", "payload": payload})


if __name__ == "__main__":
    unittest.main()
