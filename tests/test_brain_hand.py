import unittest
from unittest.mock import patch

from zexa.brain import BrainReply, BrainRouter
from zexa.hand import AccessibilityBridge


class FakeBrain:
    def __init__(self, name, answer=None, error=None):
        self.name = name
        self.answer = answer
        self.error = error
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.answer


class BrainRouterTests(unittest.TestCase):
    def test_auto_uses_online_first(self):
        router = BrainRouter(FakeBrain("groq-online", "online"), FakeBrain("local", "offline"))
        self.assertEqual(router.chat([{"role": "user", "content": "hi"}]),
                         BrainReply("online", "groq-online", False))

    def test_auto_falls_back_only_for_network_failure(self):
        router = BrainRouter(
            FakeBrain("groq-online", error=RuntimeError("Could not reach Groq API: offline")),
            FakeBrain("local", "local answer"),
        )
        self.assertEqual(router.chat([]), BrainReply("local answer", "local", True))

    def test_auto_falls_back_from_grok_to_groq_then_qwen(self):
        grok = FakeBrain("grok-xai", error=RuntimeError("Could not reach xAI API: timeout"))
        groq = FakeBrain("groq-online", "groq answer")
        qwen = FakeBrain("qwen-local", "qwen answer")
        router = BrainRouter(grok, qwen, fallbacks=[groq])
        self.assertEqual(router.chat([]), BrainReply("groq answer", "groq-online", False))
        self.assertEqual((grok.calls, groq.calls, qwen.calls), (1, 1, 0))

    def test_auto_falls_back_to_qwen_after_cloud_network_failures(self):
        grok = FakeBrain("grok-xai", error=RuntimeError("Could not reach xAI API: timeout"))
        groq = FakeBrain("groq-online", error=RuntimeError("Could not reach Groq API: offline"))
        qwen = FakeBrain("qwen-local", "local answer")
        router = BrainRouter(grok, qwen, fallbacks=[groq])
        self.assertEqual(router.chat([]), BrainReply("local answer", "qwen-local", True))

    def test_auth_or_api_errors_do_not_fallback(self):
        local = FakeBrain("local", "must not be used")
        router = BrainRouter(
            FakeBrain("groq-online", error=RuntimeError("Groq API returned HTTP 401")),
            local,
        )
        with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
            router.chat([])
        self.assertEqual(local.calls, 0)

    def test_offline_mode_does_not_call_online(self):
        online = FakeBrain("groq-online", error=AssertionError("online called"))
        router = BrainRouter(online, FakeBrain("local", "offline answer"), mode="offline")
        self.assertEqual(router.chat([]).brain, "local")

    def test_offline_mode_requires_offline_brain(self):
        with self.assertRaisesRegex(RuntimeError, "Local Qwen"):
            BrainRouter(FakeBrain("groq-online", "online"), None, mode="offline").chat([])


class AccessibilityBridgeTests(unittest.TestCase):
    def test_rejects_non_loopback_urls(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            AccessibilityBridge("a" * 32, "http://example.com:8765")

    def test_requires_token(self):
        with self.assertRaises(ValueError):
            AccessibilityBridge("short")

    def test_action_requires_explicit_approval(self):
        bridge = AccessibilityBridge("t" * 32)
        with patch.object(bridge, "_request") as request:
            with self.assertRaises(PermissionError):
                bridge.perform("tap", {"x": 10, "y": 20})
            request.assert_not_called()

    def test_rejects_unknown_actions(self):
        bridge = AccessibilityBridge("t" * 32)
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            bridge.perform("run_shell", {"command": "whoami"}, lambda *_: True)

    def test_approved_action_uses_fixed_endpoint(self):
        bridge = AccessibilityBridge("t" * 32)
        with patch.object(bridge, "_request", return_value={"ok": True}) as request:
            result = bridge.perform("back", {}, lambda *_: True)
        self.assertEqual(result, {"ok": True})
        request.assert_called_once_with(
            "POST", "/v1/action", {"action": "back", "payload": {}}
        )


if __name__ == "__main__":
    unittest.main()
