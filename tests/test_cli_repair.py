import io
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from zexa import cli


class FakeQueue:
    def __init__(self):
        self.kind = None
        self.payload = None

    def enqueue(self, kind, payload):
        self.kind = kind
        self.payload = payload
        return 42


class RepairCliTests(unittest.TestCase):
    def test_repair_check_queues_allowlisted_job(self):
        queue = FakeQueue()
        output = io.StringIO()
        with patch.object(sys, "argv", ["zexa", "repair-check"]), \
             patch.object(cli, "JobQueue", return_value=queue), \
             redirect_stdout(output):
            cli.main()
        self.assertEqual(queue.kind, "repair_check")
        self.assertEqual(queue.payload, {})
        self.assertIn("Self-check queued: #42", output.getvalue())


if __name__ == "__main__":
    unittest.main()
