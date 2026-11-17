"""Regression tests for explicit dual-brain routing and fallback boundaries."""
import unittest

from zexa.brain import BrainReply, BrainRouter


class FakeBrain:
    def __init__(self, name, response="ok", error=None):
        self.name = name
        self.response = response
        self.error = error
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        if self.error:
            raise self.error
        return self.response


class BrainRouterTests(unittest.TestCase):
    def setUp(self):
        self.messages = [{"role": "user", "content": "hello"}]

    def test_auto_uses_online_when_available(self):
        online = FakeBrain("online", "online answer")
        offline = FakeBrain("offline", "offline answer")
        result = BrainRouter(online, offline, "auto").chat(self.messages)
        self.assertEqual(result, BrainReply("online answer", "online", False))
        self.assertEqual((online.calls, offline.calls), (1, 0))

    def test_auto_falls_back_only_for_network_failure(self):
        online = FakeBrain("online", error=RuntimeError("Could not reach Groq API: timeout"))
        offline = FakeBrain("offline", "offline answer")
        result = BrainRouter(online, offline, "auto").chat(self.messages)
        self.assertEqual(result, BrainReply("offline answer", "offline", True))
        self.assertEqual((online.calls, offline.calls), (1, 1))

    def test_auto_does_not_hide_authentication_or_quota_errors(self):
        for message in ("Groq authentication failed", "Groq quota exceeded", "model not found"):
            with self.subTest(message=message):
                online = FakeBrain("online", error=RuntimeError(message))
                offline = FakeBrain("offline")
                with self.assertRaisesRegex(RuntimeError, message):
                    BrainRouter(online, offline, "auto").chat(self.messages)
                self.assertEqual(offline.calls, 0)

    def test_offline_mode_never_calls_online(self):
        online = FakeBrain("online")
        offline = FakeBrain("offline", "local answer")
        result = BrainRouter(online, offline, "offline").chat(self.messages)
        self.assertEqual(result, BrainReply("local answer", "offline", True))
        self.assertEqual((online.calls, offline.calls), (0, 1))

    def test_online_mode_does_not_fallback(self):
        online = FakeBrain("online", error=RuntimeError("Could not reach Groq API: timeout"))
        offline = FakeBrain("offline")
        with self.assertRaisesRegex(RuntimeError, "Could not reach Groq API"):
            BrainRouter(online, offline, "online").chat(self.messages)
        self.assertEqual(offline.calls, 0)

    def test_missing_provider_errors_are_explicit(self):
        with self.assertRaisesRegex(RuntimeError, "Neither online nor offline"):
            BrainRouter(None, None, "auto").chat(self.messages)
        with self.assertRaisesRegex(RuntimeError, "Online Groq brain"):
            BrainRouter(None, FakeBrain("offline"), "online").chat(self.messages)


if __name__ == "__main__":
    unittest.main()
