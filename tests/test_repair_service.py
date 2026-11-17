import unittest

from zexa.repair_service import run_repair_assessment, format_repair_notification


class RepairServiceTests(unittest.TestCase):
    def report(self):
        return {"summary": {"errors": 1, "warnings": 2}, "checks": [
            {"name": "python_version", "status": "error"},
            {"name": "groq_api_key", "status": "warning"},
            {"name": "unknown", "status": "warning"},
        ]}

    def test_doctor_and_plan_integrate_without_side_effects(self):
        calls = []
        result = run_repair_assessment(lambda: (calls.append("doctor") or self.report()))
        self.assertEqual(calls, ["doctor"])
        self.assertEqual(len(result["plan"]["findings"]), 2)
        self.assertFalse(result["actions_executed"])
        self.assertFalse(result["files_modified"])
        self.assertEqual(result["brain_analysis_status"], "not_requested")

    def test_brain_only_explains_bounded_plan(self):
        prompts = []
        result = run_repair_assessment(self.report, lambda prompt: (prompts.append(prompt) or "Review Python first."))
        self.assertEqual(result["brain_analysis_status"], "completed")
        self.assertIn("python_version", prompts[0])
        self.assertNotIn("GROQ_API_KEY", prompts[0])
        self.assertEqual(result["plan"]["findings"][0]["check"], "python_version")
        self.assertFalse(result["commands_executed"])

    def test_brain_failure_does_not_fail_diagnostics(self):
        result = run_repair_assessment(self.report, lambda _: (_ for _ in ()).throw(RuntimeError("offline")))
        self.assertEqual(result["brain_analysis_status"], "unavailable")
        self.assertEqual(len(result["plan"]["findings"]), 2)

    def test_notification_is_compact(self):
        message = format_repair_notification(run_repair_assessment(self.report))
        self.assertIn("1 errors", message)
        self.assertIn("2 warnings", message)
        self.assertLessEqual(len(message), 1000)


if __name__ == "__main__":
    unittest.main()
