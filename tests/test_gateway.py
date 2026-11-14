from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zexa.approvals import ApprovalManager
from zexa.audit import AuditLog
from zexa.gateway import ExecutionDenied, ExecutionGateway
from zexa.policy import PermissionPolicy


class ExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audit = AuditLog(Path(self.temp.name) / "audit.sqlite3")
        self.approvals = ApprovalManager(ttl_seconds=60)
        self.policy = PermissionPolicy({"files.read", "message.send"})
        self.gateway = ExecutionGateway(\n            self.policy, self.approvals, self.audit,\n            capabilities={"files.read": ("files.read", "low"), "message.send": ("message.send", "high")},\n        )

    def tearDown(self):
        self.temp.cleanup()

    def test_low_risk_action_runs_with_explicit_permission(self):
        result = self.gateway.execute(
            action="files.read", permission="files.read", risk_level="low",
            payload={"path": "notes.txt"}, handler=lambda data: data["path"],
        )
        self.assertEqual(result, "notes.txt")
        self.assertEqual(self.audit.recent(1)[0]["event_type"], "execution_completed")

    def test_denies_ungranted_permission_without_calling_handler(self):
        called = []
        with self.assertRaises(ExecutionDenied):
            self.gateway.execute(
                action="android.tap", permission="android.tap", risk_level="low",
                payload={}, handler=lambda data: called.append(True),
            )
        self.assertEqual(called, [])

    def test_high_risk_requires_exact_one_time_approval(self):
        payload = {"recipient": "client@example.test", "body": "Draft"}
        token = self.gateway.issue_approval(
            action="message.send", payload=payload, user_confirmed=True,
        ).token
        result = self.gateway.execute(
            action="message.send", permission="message.send", risk_level="high",
            payload=payload, approval_token=token, handler=lambda data: "sent",
        )
        self.assertEqual(result, "sent")
        with self.assertRaises(ExecutionDenied):
            self.gateway.execute(
                action="message.send", permission="message.send", risk_level="high",
                payload=payload, approval_token=token, handler=lambda data: "duplicate",
            )

    def test_approval_cannot_be_reused_for_changed_payload(self):
        payload = {"recipient": "one@example.test"}
        token = self.gateway.issue_approval(
            action="message.send", payload=payload, user_confirmed=True,
        ).token
        with self.assertRaises(ExecutionDenied):
            self.gateway.execute(
                action="message.send", permission="message.send", risk_level="high",
                payload={"recipient": "two@example.test"}, approval_token=token,
                handler=lambda data: "sent",
            )

    def test_caller_cannot_downgrade_registered_risk(self):\n        called = []\n        with self.assertRaises(ExecutionDenied):\n            self.gateway.execute(\n                action="message.send", permission="message.send", risk_level="low",\n                payload={}, handler=lambda data: called.append(True),\n            )\n        self.assertEqual(called, [])\n\n    def test_unknown_action_is_denied(self):\n        with self.assertRaises(ExecutionDenied):\n            self.gateway.execute(\n                action="android.tap", permission="android.tap", risk_level="low",\n                payload={}, handler=lambda data: "should not run",\n            )\n\n    def test_failed_handler_is_audited(self):
        def fail(_payload):
            raise RuntimeError("expected failure")
        with self.assertRaises(RuntimeError):
            self.gateway.execute(
                action="files.read", permission="files.read", risk_level="low",
                payload={}, handler=fail,
            )
        self.assertEqual(self.audit.recent(1)[0]["event_type"], "execution_failed")\n        self.assertNotIn("expected failure", str(self.audit.recent(1)[0]["details"]))


if __name__ == "__main__":
    unittest.main()
