import json
import unittest

from zexa.repair_jobs import create_repair_check_handler
from zexa.jobs import JobQueue, JobWorker
import tempfile
from pathlib import Path


class FakeBrain:
    def __init__(self, answer="Advisory: review the configuration."):
        self.messages = None
        self.answer = answer

    def chat(self, messages):
        self.messages = messages
        return type("Reply", (), {"text": self.answer})()


class RepairJobTests(unittest.TestCase):
    def test_runs_doctor_plan_and_brain_as_advisory_without_changes(self):
        brain = FakeBrain()
        notifications = []
        report = {
            "summary": {"total": 1, "warnings": 1, "errors": 0, "ok": 0},
            "checks": [{"name": "groq_api_key", "status": "warning"}],
        }
        handler = create_repair_check_handler(
            brain=brain,
            notifier=lambda title, message: notifications.append((title, message)),
            diagnostics=lambda: report,
        )
        result = json.loads(handler({}))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["brain_advisory"], brain.answer)
        self.assertFalse(result["automatic_changes"])
        self.assertFalse(result["commands_executed"])
        self.assertFalse(result["files_modified"])
        self.assertEqual(len(result["repair_plan"]["findings"]), 1)
        self.assertEqual(len(notifications), 1)
        self.assertNotIn("actual-secret-value", str(brain.messages))

    def test_no_findings_skips_brain_but_notifies(self):
        class MustNotRun:
            def chat(self, _messages):
                raise AssertionError("Brain should not run without findings")
        notifications = []
        handler = create_repair_check_handler(
            brain=MustNotRun(),
            notifier=lambda *args: notifications.append(args),
            diagnostics=lambda: {"summary": {}, "checks": []},
        )
        result = json.loads(handler({}))
        self.assertEqual(result["repair_plan"]["findings"], [])
        self.assertEqual(len(notifications), 1)

    def test_repair_check_runs_through_allowlisted_background_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            queue = JobQueue(Path(temp) / "jobs.sqlite3")
            job_id = queue.enqueue("repair_check", {})
            handler = create_repair_check_handler(
                diagnostics=lambda: {
                    "summary": {"total": 0, "warnings": 0, "errors": 0, "ok": 0},
                    "checks": [],
                }
            )
            worker = JobWorker(queue, {"repair_check": handler})
            self.assertEqual(worker.run_once(), "completed")
            job = queue.list_jobs()[0]
            self.assertEqual(job["id"], job_id)
            self.assertEqual(job["status"], "completed")
            result = json.loads(job["result"])
            self.assertFalse(result["automatic_changes"])

    def test_brain_failure_keeps_deterministic_plan(self):
        class BrokenBrain:
            def chat(self, _messages):
                raise RuntimeError("offline")
        handler = create_repair_check_handler(
            brain=BrokenBrain(),
            diagnostics=lambda: {
                "summary": {},
                "checks": [{"name": "python_version", "status": "error"}],
            },
        )
        result = json.loads(handler({}))
        self.assertEqual(len(result["repair_plan"]["findings"]), 1)
        self.assertIn("unavailable", result["brain_advisory"])
        self.assertFalse(result["files_modified"])


if __name__ == "__main__":
    unittest.main()
