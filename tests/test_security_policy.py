import tempfile
import unittest
from pathlib import Path

from zexa.approvals import ApprovalManager
from zexa.security import ActionGuard, AuditLog, PermissionPolicy
from zexa.skills import Skill, SkillRegistry, default_registry


class SkillPayloadValidationTests(unittest.TestCase):
    def test_validates_required_types_and_unknown_fields(self):
        registry = default_registry()
        payload = {"prompt": "Explain local-first AI."}
        self.assertEqual(registry.validate_payload("general_assistant", payload), payload)
        with self.assertRaisesRegex(ValueError, "Missing"):
            registry.validate_payload("general_assistant", {})
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            registry.validate_payload("general_assistant", {"prompt": "Hi", "extra": "no"})

    def test_boolean_is_not_accepted_as_integer(self):
        registry = SkillRegistry()
        registry.register(Skill(
            "typed", "A typed skill.", "Validate types.",
            input_schema={"count": "integer"}, output_schema={"ok": "boolean"},
        ))
        with self.assertRaisesRegex(ValueError, "integer"):
            registry.validate_payload("typed", {"count": True})

    def test_unknown_schema_types_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "supported types"):
            Skill("bad", "Description", "Instruction", input_schema={"x": "shell"})


class PermissionAndAuditTests(unittest.TestCase):
    def test_permissions_are_default_deny_and_revocable(self):
        policy = PermissionPolicy()
        with self.assertRaises(PermissionError):
            policy.require(["android.tap"])
        policy.grant("android.tap")
        self.assertTrue(policy.allows("android.tap"))
        self.assertTrue(policy.revoke("android.tap"))
        with self.assertRaises(PermissionError):
            policy.require(["android.tap"])

    def test_audit_stores_payload_hash_not_raw_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            audit = AuditLog(Path(temp) / "audit.sqlite3", clock=lambda: 123.0)
            audit.record("draft_message", "allowed", {"message": "private text"}, detail="Reviewed")
            row = audit.recent()[0]
            self.assertEqual(row["timestamp"], 123.0)
            self.assertEqual(len(row["payload_sha256"]), 64)
            self.assertNotIn("private text", str(row))

    def test_action_guard_requires_permission_and_matching_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            policy = PermissionPolicy(["android.tap"])
            audit = AuditLog(Path(temp) / "audit.sqlite3")
            guard = ActionGuard(policy, ApprovalManager(), audit)
            payload = {"x": 20, "y": 40}
            with self.assertRaisesRegex(PermissionError, "approval"):
                guard.authorize("tap", payload, ["android.tap"], consequential=True)
            grant = guard.issue_approval("tap", payload, ["android.tap"], True)
            self.assertTrue(guard.authorize(
                "tap", payload, ["android.tap"], consequential=True, approval_token=grant.token
            ))
            with self.assertRaises(PermissionError):
                guard.authorize("tap", payload, ["android.tap"], consequential=True, approval_token=grant.token)
            statuses = [row["status"] for row in audit.recent(10)]
            self.assertIn("approval_issued", statuses)
            self.assertIn("allowed", statuses)
            self.assertIn("denied", statuses)

    def test_action_guard_rejects_missing_permission_before_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            audit = AuditLog(Path(temp) / "audit.sqlite3")
            guard = ActionGuard(PermissionPolicy(), ApprovalManager(), audit)
            with self.assertRaises(PermissionError):
                guard.issue_approval("write_file", {"path": "notes.txt"}, ["filesystem.write"], True)
            self.assertEqual(audit.recent()[0]["status"], "denied")


if __name__ == "__main__":
    unittest.main()
