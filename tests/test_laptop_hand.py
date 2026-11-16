from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zexa.approvals import ApprovalManager
from zexa.audit import AuditLog
from zexa.capabilities import CapabilityController
from zexa.laptop_hand import LaptopWorkspace, build_laptop_capabilities
from zexa.policy import PermissionPolicy


class LaptopWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        self.workspace = LaptopWorkspace(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_lists_only_items_inside_selected_workspace(self):
        (self.root / "notes").mkdir()
        (self.root / "notes" / "lesson.txt").write_text("hello", encoding="utf-8")
        listing = self.workspace.list_directory(".")
        self.assertEqual(listing["entries"][0]["name"], "notes")
        nested = self.workspace.list_directory("notes")
        self.assertEqual(nested["entries"][0]["name"], "lesson.txt")
        self.assertTrue(nested["entries"][0]["readable_text"])

    def test_rejects_absolute_parent_and_windows_paths(self):
        for path in ("../outside.txt", "/etc/passwd", "notes/../../outside", r"..\\outside.txt", "C:/Windows"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.workspace.read_text(path)

    def test_reads_bounded_utf8_text_with_digest(self):
        source = self.root / "lesson.md"
        source.write_text("A useful lesson.", encoding="utf-8")
        result = self.workspace.read_text("lesson.md")
        self.assertEqual(result["content"], "A useful lesson.")
        self.assertEqual(len(result["sha256"]), 64)

    def test_rejects_binary_invalid_utf8_and_oversized_files(self):
        (self.root / "binary.txt").write_bytes(bytes([0xff, 0xfe]))
        (self.root / "large.txt").write_bytes(b"x" * 256_001)
        for name in ("binary.txt", "large.txt"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.workspace.read_text(name)

    def test_excludes_credentials_and_non_text_files(self):
        (self.root / ".env").write_text("TOKEN=secret", encoding="utf-8")
        (self.root / "api_token.txt").write_text("secret", encoding="utf-8")
        (self.root / "model.gguf").write_bytes(b"GGUF")
        for name in (".env", "api_token.txt", "model.gguf"):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                self.workspace.read_text(name)

    def test_symlink_is_never_read_or_listed(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.root / "escape.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are unavailable on this platform.")
        self.assertEqual(self.workspace.list_directory(".")["entries"], [])
        with self.assertRaises(PermissionError):
            self.workspace.read_text("escape.txt")

    def test_write_is_atomic_and_does_not_overwrite_by_default(self):
        result = self.workspace.write_text("draft.md", "First draft.")
        self.assertTrue(result["written"])
        self.assertEqual((self.root / "draft.md").read_text(encoding="utf-8"), "First draft.")
        with self.assertRaises(FileExistsError):
            self.workspace.write_text("draft.md", "Second draft.")
        self.workspace.write_text("draft.md", "Second draft.", overwrite=True)
        self.assertEqual((self.root / "draft.md").read_text(encoding="utf-8"), "Second draft.")
        self.assertFalse(any(item.name.startswith(".zexa-write-") for item in self.root.iterdir()))

    def test_write_rejects_sensitive_names_and_empty_content(self):
        with self.assertRaises(PermissionError):
            self.workspace.write_text(".env", "TOKEN=secret")
        with self.assertRaises(ValueError):
            self.workspace.write_text("empty.txt", "  ")

    def test_capability_contracts_require_permission_and_exact_write_approval(self):
        audit = AuditLog(Path(self.temp.name) / "audit.sqlite3")
        approvals = ApprovalManager(ttl_seconds=60)
        policy = PermissionPolicy({"laptop.workspace.read", "laptop.workspace.write"})
        controller = CapabilityController(
            policy, approvals, audit, build_laptop_capabilities(self.workspace)
        )
        payload = {
            "relative_path": "approved.txt",
            "content": "Approved",
            "overwrite": False,
        }
        with self.assertRaises(PermissionError):
            controller.execute("laptop.workspace.write", payload)
        grant = controller.issue_approval(
            "laptop.workspace.write", payload, user_confirmed=True
        )
        result = controller.execute(
            "laptop.workspace.write", payload, approval_token=grant.token
        )
        self.assertTrue(result["written"])
        with self.assertRaises(PermissionError):
            controller.execute(
                "laptop.workspace.write", payload, approval_token=grant.token
            )


if __name__ == "__main__":
    unittest.main()
