import unittest
from pathlib import Path

from zexa.doctor import run_diagnostics


class DoctorTests(unittest.TestCase):
    def test_report_is_read_only_and_redacts_credentials(self):
        secret = "super-secret-value"
        report = run_diagnostics(
            which=lambda name: None,
            environ={"GROQ_API_KEY": secret, "GROQ_MODEL": "test-model"},
            cwd=Path("/nonexistent"),
        )
        rendered = str(report)
        self.assertNotIn(secret, rendered)
        self.assertTrue(report["actions_executed"] is False)
        self.assertFalse(report["secrets_exposed"])
        self.assertFalse(report["repair"]["automatic_changes"])
        self.assertEqual(report["mode"], "read_only")

    def test_detects_configured_brain_and_termux(self):
        report = run_diagnostics(
            which=lambda name: "/fake/" + name,
            environ={
                "PREFIX": "/data/data/com.termux/files/usr",
                "GROQ_API_KEY": "secret",
                "GROQ_MODEL": "model",
                "ZEXA_BRIDGE_TOKEN": "token",
            },
            cwd=Path("/tmp"),
        )
        statuses = {item["name"]: item["status"] for item in report["checks"]}
        self.assertEqual(statuses["groq_api_key"], "ok")
        self.assertEqual(statuses["groq_model"], "ok")
        self.assertEqual(statuses["android_termux"], "ok")
        self.assertEqual(statuses["android_bridge_config"], "ok")
        self.assertEqual(statuses["command:llama-cli"], "ok")

    def test_missing_optional_capabilities_are_not_fatal(self):
        report = run_diagnostics(which=lambda _name: None, environ={}, cwd=Path("/tmp"))
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["repair"]["approval_required_for_changes"], True)


if __name__ == "__main__":
    unittest.main()
