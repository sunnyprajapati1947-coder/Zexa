from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zexa.audit import AuditLog
from zexa.policy import PermissionPolicy


class PermissionPolicyTests(unittest.TestCase):
    def test_denies_ungranted_permission(self):
        decision = PermissionPolicy().decide("android.tap")
        self.assertFalse(decision.allowed)
        self.assertIn("not explicitly granted", decision.reason)

    def test_requires_approval_for_high_risk(self):
        policy = PermissionPolicy({"android.tap", "message.send"})
        denied = policy.decide("message.send", risk_level="high")
        allowed = policy.decide("message.send", risk_level="high", approved=True)
        self.assertFalse(denied.allowed)
        self.assertTrue(denied.approval_required)
        self.assertTrue(allowed.allowed)

    def test_revocation_takes_effect(self):
        policy = PermissionPolicy({"files.read"})
        self.assertTrue(policy.decide("files.read").allowed)
        self.assertTrue(policy.revoke("files.read"))
        self.assertFalse(policy.decide("files.read").allowed)

    def test_rejects_invalid_risk(self):
        with self.assertRaises(ValueError):
            PermissionPolicy({"files.read"}).decide("files.read", risk_level="unknown")


class AuditLogTests(unittest.TestCase):
    def test_persists_and_redacts_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            log = AuditLog(Path(directory) / "audit.sqlite3")
            event_id = log.record(
                "tool_execution",
                action="email.send",
                decision="approval_required",
                details={
                    "api_key": "do-not-store",
                    "summary": "Authorization: Bearer abc.def.ghi",
                    "nested": {"password": "hidden", "count": 2},
                },
            )
            event = log.recent(1)[0]
            self.assertEqual(event["id"], event_id)
            self.assertEqual(event["details"]["api_key"], "[REDACTED]")
            self.assertNotIn("abc.def.ghi", event["details"]["summary"])
            self.assertEqual(event["details"]["nested"]["password"], "[REDACTED]")

    def test_rejects_invalid_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            log = AuditLog(Path(directory) / "audit.sqlite3")
            with self.assertRaises(ValueError):
                log.recent(0)


if __name__ == "__main__":
    unittest.main()
