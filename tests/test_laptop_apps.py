from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys

from zexa.laptop_apps import LaptopAppRegistry


class LaptopAppRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.executable = Path(sys.executable).resolve()
        self.manifest = self.root / "apps.json"

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, apps=None):
        payload = {
            "version": 1,
            "apps": apps if apps is not None else [{
                "id": "python-tool",
                "executable": str(self.executable),
                "arguments": ["--version"],
                "description": "Python version tool",
            }],
        }
        self.manifest.write_text(json.dumps(payload), encoding="utf-8")

    def test_loads_only_owner_configured_fixed_app_entries(self):
        self.write_manifest()
        registry = LaptopAppRegistry(self.manifest)
        self.assertEqual(registry.list_apps(), [{
            "app_id": "python-tool",
            "description": "Python version tool",
        }])

    def test_rejects_unknown_fields_duplicate_ids_and_invalid_arguments(self):
        self.write_manifest([{
            "id": "python-tool", "executable": str(self.executable),
            "arguments": ["--version"], "description": "Tool", "shell": True,
        }])
        with self.assertRaises(ValueError):
            LaptopAppRegistry(self.manifest)
        self.write_manifest([
            {"id": "python-tool", "executable": str(self.executable), "arguments": [], "description": "One"},
            {"id": "python-tool", "executable": str(self.executable), "arguments": [], "description": "Two"},
        ])
        with self.assertRaises(ValueError):
            LaptopAppRegistry(self.manifest)
        self.write_manifest([{
            "id": "python-tool", "executable": str(self.executable),
            "arguments": ["--version\nmalicious"], "description": "Tool",
        }])
        with self.assertRaises(ValueError):
            LaptopAppRegistry(self.manifest)

    def test_rejects_writable_executable_and_manifest_symlink(self):
        if os.name == "nt":
            self.skipTest("POSIX executable mode checks are platform-specific.")
        self.write_manifest()
        original = self.executable.stat().st_mode
        try:
            self.executable.chmod(original | 0o020)
            with self.assertRaises(PermissionError):
                LaptopAppRegistry(self.manifest)
        finally:
            self.executable.chmod(original)
        target = self.root / "real.json"
        self.write_manifest()
        self.manifest.rename(target)
        self.manifest.symlink_to(target)
        with self.assertRaises(PermissionError):
            LaptopAppRegistry(self.manifest)

    def test_rejects_shell_like_executable_names(self):
        self.write_manifest([{
            "id": "shell", "executable": "python",
            "arguments": ["--version"], "description": "Not absolute",
        }])
        with self.assertRaises(ValueError):
            LaptopAppRegistry(self.manifest)


if __name__ == "__main__":
    unittest.main()
