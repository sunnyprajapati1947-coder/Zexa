import os
import sys
import unittest
from unittest.mock import patch

from zexa import cli


class FakeBridge:
    def __init__(self, token, base_url):
        self.token = token
        self.base_url = base_url

    def status(self):
        return {"ok": True, "bridge_enabled": True}

    def screen(self):
        return {"ok": True, "nodes": []}

    def perform(self, action, payload, approve=None):
        if approve is None or approve(action, payload) is not True:
            raise PermissionError("not approved")
        return {"ok": True, "action": action, "payload": payload}


class BridgeCliTests(unittest.TestCase):
    def invoke(self, argv, confirmation=None):
        patches = [
            patch.object(sys, "argv", ["zexa", "bridge", *argv]),
            patch.object(cli, "load_env_file"),
            patch.dict(os.environ, {"ZEXA_BRIDGE_TOKEN": "t" * 32, "ZEXA_BRIDGE_URL": "http://127.0.0.1:8765"}),
            patch.object(cli, "AccessibilityBridge", FakeBridge),
        ]
        for item in patches:
            item.start()
        try:
            if confirmation is None:
                cli.main()
            else:
                with patch("builtins.input", return_value=confirmation):
                    cli.main()
        finally:
            for item in reversed(patches):
                item.stop()

    def test_status_and_screen_are_read_only(self):
        with patch("builtins.print") as output:
            self.invoke(["status"])
            self.invoke(["screen"])
        self.assertEqual(output.call_count, 2)

    def test_action_requires_exact_confirmation(self):
        with patch("builtins.print") as output:
            self.invoke(["action", "back", "{}"], confirmation="no")
        self.assertIn("Android action cancelled.", output.call_args.args[0])

    def test_approved_action_uses_allowlisted_client(self):
        with patch("builtins.print") as output:
            self.invoke(["action", "back", "{}"], confirmation="APPROVE")
        self.assertTrue(any("APPROVE" not in str(call) for call in output.call_args_list))


if __name__ == "__main__":
    unittest.main()
