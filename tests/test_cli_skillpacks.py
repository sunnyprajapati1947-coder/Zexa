import json
import sys
import unittest
from unittest.mock import patch

from zexa import cli


class SkillpackCliTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "imported_count": 320,
            "enabled_count": 0,
            "sources": [{}, {}, {}],
            "skills": [
                {
                    "name": "meeting_notes",
                    "description": "Organize user-provided meeting notes.",
                    "license": "MIT",
                    "review_required": False,
                    "enabled": False,
                }
            ],
        }

    def test_status_reports_counts_without_enabling_imports(self):
        with (
            patch.object(sys, "argv", ["zexa", "skillpacks", "status"]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "load_imported_manifest", return_value=self.manifest),
            patch("builtins.print") as output,
        ):
            cli.main()
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["imported_count"], 320)
        self.assertEqual(result["enabled_count"], 0)
        self.assertEqual(result["execution"], "disabled; imported references are not executable")

    def test_list_returns_only_read_only_metadata(self):
        with (
            patch.object(sys, "argv", ["zexa", "skillpacks", "list", "--limit", "1"]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "load_imported_manifest", return_value=self.manifest),
            patch("builtins.print") as output,
        ):
            cli.main()
        result = json.loads(output.call_args.args[0])
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["enabled"])
        self.assertNotIn("source_path", result[0])

    def test_list_limit_is_bounded(self):
        with (
            patch.object(sys, "argv", ["zexa", "skillpacks", "list", "--limit", "0"]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "load_imported_manifest", return_value=self.manifest),
        ):
            with self.assertRaises(SystemExit):
                cli.main()


if __name__ == "__main__":
    unittest.main()
