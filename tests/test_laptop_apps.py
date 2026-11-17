from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
import sys

from zexa.laptop_apps import LaptopAppRegistry


class LaptopAppRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.executable = self.root / "python-executable"
        shutil.copy2(Path(sys.executable).resolve(), self.executable)
        self.executable.chmod(stat.S_IMODE(self.executable.stat().st_mode) & ~0o022)
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
        writable_executable = self.root / "writable-python"
        shutil.copy2(self.executable, writable_executable)
        writable_executable.chmod(stat.S_IMODE(writable_executable.stat().st_mode) | 0o020)
        self.write_manifest([{
            "id": "python-tool", "executable": str(writable_executable),
            "arguments": ["--version"], "description": "Tool",
        }])
        with self.assertRaises(PermissionError):
            LaptopAppRegistry(self.manifest)
        target = self.root / "real.json"
        self.write_manifest()
        self.manifest.rename(target)
        self.manifest.symlink_to(target)
        with self.assertRaises(PermissionError):
            LaptopAppRegistry(self.manifest)

    def test_rejects_symlinked_ancestor_directories(self):
        if os.name == "nt":
            self.skipTest("POSIX symlink behavior is platform-specific.")
        real_dir = self.root / "real-config"
        real_dir.mkdir()
        alias = self.root / "config-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        nested = alias / "nested"
        nested.mkdir()
        manifest = nested / "apps.json"
        manifest.write_text(json.dumps({
            "version": 1,
            "apps": [{
                "id": "python-tool",
                "executable": str(self.executable),
                "arguments": ["--version"],
                "description": "Python version tool",
            }],
        }), encoding="utf-8")
        with self.assertRaises(PermissionError):
            LaptopAppRegistry(manifest)

        executable_alias = self.root / "bin-alias"
        executable_alias.symlink_to(self.root, target_is_directory=True)
        executable = executable_alias / self.executable.name
        self.write_manifest([{
            "id": "python-tool",
            "executable": str(executable),
            "arguments": ["--version"],
            "description": "Python version tool",
        }])
        with self.assertRaises(ValueError):
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
