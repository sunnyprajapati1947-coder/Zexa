import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from zexa import cli


class FakeQueue:
    def __init__(self):
        self.cancelled = []
        self.retried = []
        self.enqueued = []

    def enqueue(self, kind, payload, **kwargs):
        self.enqueued.append((kind, payload, kwargs))
        return 42

    def cancel(self, job_id):
        self.cancelled.append(job_id)
        return True

    def retry(self, job_id):
        self.retried.append(job_id)
        return True


class JobCliTests(unittest.TestCase):
    def test_schedule_skill_loads_selected_env_file_before_queueing(self):
        queue = FakeQueue()
        with (
            patch.object(sys, "argv", [
                "zexa", "schedule-skill", "general_assistant",
                '{"prompt":"prepare a draft"}',
            ]),
            patch.dict(os.environ, {"ZEXA_ENV_FILE": "/tmp/zexa-test.env"}),
            patch.object(cli, "load_env_file") as load_env,
            patch.object(cli, "JobQueue", return_value=queue),
            patch("builtins.print") as output,
        ):
            cli.main()
        load_env.assert_called_once_with(Path("/tmp/zexa-test.env"))
        self.assertEqual(queue.enqueued[0][0], "skill_draft")
        self.assertEqual(queue.enqueued[0][1]["name"], "general_assistant")
        self.assertIn("42", output.call_args.args[0])

    def test_job_cancel_and_retry_commands(self):
        queue = FakeQueue()
        with (
            patch.object(cli, "load_env_file"),
            patch.object(cli, "JobQueue", return_value=queue),
            patch.object(sys, "argv", ["zexa", "job", "cancel", "7"]),
            patch("builtins.print") as output,
        ):
            cli.main()
        self.assertEqual(queue.cancelled, [7])
        self.assertIn("cancelled", output.call_args.args[0])

        with (
            patch.object(cli, "load_env_file"),
            patch.object(cli, "JobQueue", return_value=queue),
            patch.object(sys, "argv", ["zexa", "job", "retry", "8"]),
            patch("builtins.print") as output,
        ):
            cli.main()
        self.assertEqual(queue.retried, [8])
        self.assertIn("retry", output.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
