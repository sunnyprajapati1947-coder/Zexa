import unittest

from zexa.repair import build_repair_plan


class RepairPlanTests(unittest.TestCase):
    def test_builds_only_known_proposals_without_executing(self):
        report = {"checks": [
            {"name": "groq_api_key", "status": "warning"},
            {"name": "command:llama-cli", "status": "info"},
            {"name": "android_bridge_config", "status": "info"},
            {"name": "unknown_check", "status": "error"},
            {"name": "project_env_file", "status": "warning"},
        ]}
        plan = build_repair_plan(report)
        self.assertEqual(plan["mode"], "proposal_only")
        self.assertFalse(plan["automatic_changes"])
        self.assertFalse(plan["commands_executed"])
        self.assertFalse(plan["files_modified"])
        self.assertEqual([item["check"] for item in plan["findings"]], [
            "groq_api_key", "project_env_file"
        ])
        self.assertTrue(all(item["approval_required"] for item in plan["findings"]))
        self.assertTrue(all(item["execution"] == "not_executed" for item in plan["findings"]))

    def test_untrusted_names_and_payloads_never_become_commands(self):
        report = {"checks": [
            {"name": "os.system('rm -rf /')", "status": "error"},
            {"name": "python_version", "status": "error", "command": "arbitrary"},
        ]}
        plan = build_repair_plan(report)
        self.assertEqual(len(plan["findings"]), 1)
        self.assertNotIn("command", plan["findings"][0])
        self.assertNotIn("os.system", str(plan))

    def test_invalid_report_is_rejected(self):
        with self.assertRaises(ValueError):
            build_repair_plan({"unexpected": []})


if __name__ == "__main__":
    unittest.main()
