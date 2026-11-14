import json
import tempfile
import unittest
from pathlib import Path

from zexa.skillpacks import load_imported_manifest


class ImportedManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "index.json"
        self.entry = {
            "name": "meeting_notes",
            "description": "Organize user-provided meeting notes.",
            "source_repo": "example/skills",
            "source_commit": "a" * 40,
            "source_path": "skills/meeting-notes/SKILL.md",
            "license": "MIT",
            "sha256": "b" * 64,
            "review_required": False,
            "warnings": [],
            "enabled": False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, entry=None):
        item = entry or self.entry
        self.path.write_text(json.dumps({
            "schema_version": 1,
            "imported_count": 1,
            "enabled_count": 0,
            "sources": [],
            "skills": [item],
        }), encoding="utf-8")

    def test_loads_valid_disabled_manifest(self):
        self.write_manifest()
        manifest = load_imported_manifest(self.path)
        self.assertEqual(manifest["imported_count"], 1)
        self.assertFalse(manifest["skills"][0]["enabled"])

    def test_rejects_enabled_entry_and_path_traversal(self):
        enabled = dict(self.entry, enabled=True)
        self.write_manifest(enabled)
        with self.assertRaisesRegex(ValueError, "cannot be enabled"):
            load_imported_manifest(self.path)
        traversal = dict(self.entry, source_path="../outside/SKILL.md")
        self.write_manifest(traversal)
        with self.assertRaisesRegex(ValueError, "path traversal"):
            load_imported_manifest(self.path)

    def test_rejects_count_mismatch_and_duplicate_names(self):
        self.write_manifest()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data["imported_count"] = 2
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "count"):
            load_imported_manifest(self.path)
        data["imported_count"] = 2
        data["skills"].append(dict(self.entry))
        self.path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_imported_manifest(self.path)


if __name__ == "__main__":
    unittest.main()
