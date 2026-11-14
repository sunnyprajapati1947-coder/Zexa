import tempfile
import unittest
from pathlib import Path

from zexa.skillpacks import inspect_skill_file


class SkillpackSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, name, description, body):
        path = self.root / "SKILL.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n{body}\n",
            encoding="utf-8",
        )
        return path

    def test_imports_safe_skill_as_reviewable_reference(self):
        path = self.write_skill(
            "meeting_notes",
            "Organize user-provided meeting notes.",
            "Summarize supplied notes and mark uncertain details.",
        )
        item = inspect_skill_file(
            path, self.root, "example/skills", "a" * 40, "MIT",
        )
        self.assertEqual(item.name, "meeting_notes")
        self.assertFalse(item.review_required)

    def test_excludes_restricted_topic_content(self):
        path = self.write_skill(
            "restricted_topic",
            "A skill focused on gambling services.",
            "This content is excluded from the import pack.",
        )
        with self.assertRaisesRegex(ValueError, "safe import scope"):
            inspect_skill_file(
                path, self.root, "example/skills", "a" * 40, "MIT",
            )


if __name__ == "__main__":
    unittest.main()
