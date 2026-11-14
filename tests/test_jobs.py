import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from zexa.jobs import JobQueue, JobWorker


class JobQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = JobQueue(Path(self.temp.name) / "jobs.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_enqueue_and_run_allowlisted_handler(self):
        job_id = self.queue.enqueue("test_echo", {"message": "hello"})
        worker = JobWorker(self.queue, {"test_echo": lambda data: data["message"]})
        self.assertEqual(worker.run_once(), "completed")
        job = self.queue.list_jobs()[0]
        self.assertEqual(job["id"], job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["result"], "hello")
        self.assertEqual(job["attempts"], 1)

    def test_future_job_is_not_claimed_early(self):
        self.queue.enqueue(
            "test_echo", {"message": "later"},
            run_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.assertIsNone(self.queue.claim_due())

    def test_failed_job_retries_then_fails(self):
        self.queue.enqueue("test_fail", {}, max_attempts=2)
        worker = JobWorker(self.queue, {"test_fail": lambda _: (_ for _ in ()).throw(RuntimeError("temporary"))})
        self.assertEqual(worker.run_once(), "pending")
        self.assertEqual(worker.run_once(), "failed")
        self.assertEqual(self.queue.list_jobs()[0]["attempts"], 2)

    def test_unknown_job_kind_never_executes_arbitrary_payload(self):
        self.queue.enqueue("not_registered", {"command": "echo unsafe"})
        self.assertEqual(JobWorker(self.queue, {}).run_once(), "failed")
        self.assertEqual(self.queue.list_jobs()[0]["status"], "failed")

    def test_rejects_naive_schedule_and_invalid_kind(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            self.queue.enqueue("test", {}, run_at=datetime.now())
        with self.assertRaises(ValueError):
            self.queue.enqueue("Run-Shell", {})

    def test_pending_job_can_be_cancelled_but_running_job_cannot(self):
        pending_id = self.queue.enqueue("test_echo", {"message": "later"})
        self.assertTrue(self.queue.cancel(pending_id))
        self.assertEqual(self.queue.list_jobs()[0]["status"], "cancelled")
        running_id = self.queue.enqueue("test_echo", {"message": "now"})
        claimed = self.queue.claim_due()
        self.assertEqual(claimed["id"], running_id)
        self.assertFalse(self.queue.cancel(running_id))

    def test_failed_job_can_be_retried_with_fresh_attempt_budget(self):
        job_id = self.queue.enqueue("test_fail", {}, max_attempts=1)
        worker = JobWorker(self.queue, {"test_fail": lambda _: (_ for _ in ()).throw(RuntimeError("private customer data"))})
        self.assertEqual(worker.run_once(), "failed")
        failed = self.queue.list_jobs()[0]
        self.assertEqual(failed["last_error"], "RuntimeError")
        self.assertTrue(self.queue.retry(job_id))
        retried = self.queue.list_jobs()[0]
        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["attempts"], 0)
        self.assertEqual(retried["last_error"], "")

    def test_default_database_path_is_stable_and_configurable(self):
        import os
        with patch.dict(os.environ, {"ZEXA_JOB_DB": str(Path(self.temp.name) / "configured.db")}):
            configured = JobQueue()
        self.assertEqual(configured.path, Path(self.temp.name) / "configured.db")


if __name__ == "__main__":
    unittest.main()
