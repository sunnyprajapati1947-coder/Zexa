import unittest

from zexa.repair_patch import build_patch_proposal


class RepairPatchTests(unittest.TestCase):
    def test_builds_diff_without_applying_candidate(self):
        original = "def answer():\n    return 1\n"
        candidate = "def answer():\n    return 2\n"
        proposal = build_patch_proposal("src/zexa/example.py", original, candidate)
        self.assertEqual(proposal["status"], "proposal_only")
        self.assertIn("-    return 1", proposal["diff"])
        self.assertIn("+    return 2", proposal["diff"])
        self.assertFalse(proposal["files_modified"])
        self.assertFalse(proposal["candidate_executed"])
        self.assertEqual(original, "def answer():\n    return 1\n")

    def test_rejects_paths_outside_explicit_allowlist(self):
        for path in ("../secret.py", "/tmp/evil.py", ".env", ".github/workflows/ci.yml",
                     "src/zexa/../secret.py", "tests/helper.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_patch_proposal(path, "x", "y")

    def test_rejects_invalid_python_syntax(self):
        with self.assertRaisesRegex(ValueError, "syntax is invalid"):
            build_patch_proposal("src/zexa/broken.py", "x = 1\n", "def broken(:\n")

    def test_rejects_identical_or_oversized_candidate(self):
        with self.assertRaisesRegex(ValueError, "identical"):
            build_patch_proposal("README.md", "same", "same")
        with self.assertRaisesRegex(ValueError, "256 KiB"):
            build_patch_proposal("README.md", "", "x" * (256 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
