from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zexa.approvals import ApprovalManager
from zexa.audit import AuditLog
from zexa.capabilities import CapabilityController, CapabilitySpec
from zexa.policy import PermissionPolicy


class CapabilityControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.audit = AuditLog(Path(self.temp.name) / "audit.sqlite3")
        self.approvals = ApprovalManager(ttl_seconds=60)
        self.policy = PermissionPolicy({"files.read", "message.send"})
        self.calls = []
        self.controller = CapabilityController(
            self.policy,
            self.approvals,
            self.audit,
            {
                "files.read": CapabilitySpec(
                    name="files.read",
                    description="Read a file in an approved workspace.",
                    permission="files.read",
                    risk_level="low",
                    platform="core",
                    input_schema={"path": "string"},
                    output_schema={"content": "string"},
                    handler=lambda data: self.calls.append(data) or {"content": "sample"},
                ),
                "message.send": CapabilitySpec(
                    name="message.send",
                    description="Send a user-approved message.",
                    permission="message.send",
                    risk_level="high",
                    platform="cloud",
                    input_schema={"recipient": "string", "body": "string"},
                    output_schema={"sent": "boolean"},
                    handler=lambda data: {"sent": True},
                ),
            },
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_registered_low_risk_handler_runs_through_gateway(self):
        result = self.controller.execute("files.read", {"path": "notes.txt"})
        self.assertEqual(result, {"content": "sample"})
        self.assertEqual(self.calls, [{"path": "notes.txt"}])
        self.assertEqual(self.audit.recent(1)[0]["event_type"], "execution_completed")

    def test_unknown_capability_never_runs_a_handler(self):
        with self.assertRaisesRegex(PermissionError, "not registered"):
            self.controller.execute("shell.run", {"command": "echo unsafe"})
        self.assertEqual(self.calls, [])

    def test_ungranted_permission_is_denied(self):
        policy = PermissionPolicy()
        controller = CapabilityController(
            policy, self.approvals, self.audit,
            {"files.read": CapabilitySpec(
                "files.read", "Read", "files.read", "low", "core",
                {"path": "string"}, lambda data: {"content": "secret"},
                {"content": "string"},
            )},
        )
        with self.assertRaises(PermissionError):
            controller.execute("files.read", {"path": "notes.txt"})

    def test_high_risk_capability_requires_exact_one_time_approval(self):
        payload = {"recipient": "person@example.test", "body": "Hello"}
        token = self.controller.issue_approval(
            "message.send", payload, user_confirmed=True
        ).token
        self.assertEqual(
            self.controller.execute("message.send", payload, approval_token=token),
            {"sent": True},
        )
        with self.assertRaises(PermissionError):
            self.controller.execute("message.send", payload, approval_token=token)

    def test_approval_does_not_apply_to_changed_input(self):
        payload = {"recipient": "one@example.test", "body": "Hello"}
        token = self.controller.issue_approval(
            "message.send", payload, user_confirmed=True
        ).token
        with self.assertRaises(PermissionError):
            self.controller.execute(
                "message.send",
                {"recipient": "two@example.test", "body": "Hello"},
                approval_token=token,
            )

    def test_schema_rejects_missing_extra_and_wrong_types(self):
        with self.assertRaisesRegex(ValueError, "missing fields"):
            self.controller.execute("files.read", {})
        with self.assertRaisesRegex(ValueError, "unexpected fields"):
            self.controller.execute("files.read", {"path": "x", "shell": True})
        with self.assertRaisesRegex(ValueError, "must be string"):
            self.controller.execute("files.read", {"path": 12})

    def test_boolean_is_not_accepted_as_integer(self):
        controller = CapabilityController(
            self.policy, self.approvals, self.audit,
            {"counter.add": CapabilitySpec(
                "counter.add", "Add a count", "files.read", "low", "core",
                {"count": "integer"}, lambda data: {"ok": True},
            )},
        )
        with self.assertRaisesRegex(ValueError, "must be integer"):
            controller.execute("counter.add", {"count": True})

    def test_non_finite_json_is_rejected_before_handler(self):
        with self.assertRaisesRegex(ValueError, "finite JSON"):
            self.controller.execute("files.read", {"path": float("nan")})
        self.assertEqual(self.calls, [])

    def test_handler_output_must_match_declared_schema(self):
        controller = CapabilityController(
            self.policy, self.approvals, self.audit,
            {"files.read": CapabilitySpec(
                "files.read", "Read", "files.read", "low", "core",
                {"path": "string"}, lambda data: {"content": 42},
                {"content": "string"},
            )},
        )
        with self.assertRaisesRegex(ValueError, "output field 'content' must be string"):
            controller.execute("files.read", {"path": "notes.txt"})
        self.assertEqual(self.audit.recent(1)[0]["event_type"], "execution_failed")

    def test_handler_is_not_exposed_in_capability_metadata(self):
        metadata = self.controller.list_capabilities()
        self.assertEqual([item["name"] for item in metadata], ["files.read", "message.send"])
        self.assertNotIn("handler", metadata[0])
        self.assertEqual(metadata[0]["platform"], "core")

    def test_capability_contract_rejects_unknown_platform_and_risk(self):
        with self.assertRaisesRegex(ValueError, "platform"):
            CapabilitySpec(
                "files.read", "Read", "files.read", "low", "remote",
                {"path": "string"}, lambda data: {},
            )
        with self.assertRaisesRegex(ValueError, "risk"):
            CapabilitySpec(
                "files.read", "Read", "files.read", "untrusted", "core",
                {"path": "string"}, lambda data: {},
            )


if __name__ == "__main__":
    unittest.main()
