import hashlib
import tempfile
import unittest
from pathlib import Path

from zexa.approvals import ApprovalManager
from zexa.repair_transaction import RepairTransaction


class RepairTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "notes.txt").write_text("before", encoding="utf-8")
        self.approvals = ApprovalManager()
        self.tx = RepairTransaction(self.root, self.approvals)

    def tearDown(self):
        self.temp.cleanup()

    def _approved_apply(self, replacement):
        preview = self.tx.preview("notes.txt", replacement)
        payload = {
            "path": preview["path"],
            "original_sha256": preview["original_sha256"],
            "replacement_sha256": preview["replacement_sha256"],
        }
        grant = self.approvals.issue("repair.replace_file", payload, True)
        return self.tx.apply("notes.txt", replacement, grant.token)

    def test_preview_is_read_only(self):
        preview = self.tx.preview("notes.txt", "after")
        self.assertEqual((self.root / "notes.txt").read_text(), "before")
        self.assertTrue(preview["approval_required"])
        self.assertFalse(list(self.root.rglob("*.bak")))

    def test_apply_requires_matching_approval_and_creates_backup(self):
        with self.assertRaises(PermissionError):
            self.tx.apply("notes.txt", "after", "not-a-token")
        result = self._approved_apply("after")
        self.assertEqual(result["status"], "applied")
        self.assertEqual((self.root / "notes.txt").read_text(), "after")
        self.assertTrue((self.root / result["backup"]).is_file())

    def test_rollback_requires_new_approval_and_restores_backup(self):
        result = self._approved_apply("after")
        backup = self.root / result["backup"]
        current = (self.root / "notes.txt").read_bytes()
        original = backup.read_bytes()
        payload = {
            "path": "notes.txt",
            "current_sha256": hashlib.sha256(current).hexdigest(),
            "restore_sha256": hashlib.sha256(original).hexdigest(),
        }
        grant = self.approvals.issue("repair.rollback_file", payload, True)
        rolled = self.tx.rollback("notes.txt", result["backup"], result["applied_sha256"], grant.token)
        self.assertEqual(rolled["status"], "rolled_back")
        self.assertEqual((self.root / "notes.txt").read_text(), "before")

    def test_refuses_path_traversal_and_symlink(self):
        with self.assertRaises(ValueError):
            self.tx.preview("../outside.txt", "bad")
        outside = self.root.parent / "outside-zexa.txt"
        outside.write_text("outside")
        try:
            (self.root / "link.txt").symlink_to(outside)
            with self.assertRaises(ValueError):
                self.tx.preview("link.txt", "bad")
        finally:
            outside.unlink(missing_ok=True)

    def test_refuses_rollback_if_file_changed_after_repair(self):
        result = self._approved_apply("after")
        (self.root / "notes.txt").write_text("manual edit")
        payload = {
            "path": "notes.txt",
            "current_sha256": hashlib.sha256(b"manual edit").hexdigest(),
            "restore_sha256": hashlib.sha256(b"before").hexdigest(),
        }
        grant = self.approvals.issue("repair.rollback_file", payload, True)
        with self.assertRaises(RuntimeError):
            self.tx.rollback("notes.txt", result["backup"], result["applied_sha256"], grant.token)


if __name__ == "__main__":
    unittest.main()
