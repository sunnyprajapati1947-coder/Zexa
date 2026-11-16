import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from zexa.api import make_handler, serve
from zexa.jobs import JobQueue


class LocalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = JobQueue(Path(self.temp.name) / "jobs.sqlite3")
        self.token = "t" * 40
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.token, self.queue)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, method="GET", payload=None, token=None):
        data = None if payload is None else json.dumps(payload).encode()
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=data, headers=headers, method=method)
        return urlopen(request, timeout=3)

    def test_health_requires_bearer_token(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/v1/health")
        self.assertEqual(caught.exception.code, 401)
        response = self.request("/v1/health", token=self.token)
        self.assertEqual(response.status, 200)
        self.assertTrue(json.loads(response.read())["ok"])

    def test_notification_endpoint_only_queues_allowlisted_job(self):
        response = self.request(
            "/v1/notifications", method="POST",
            payload={"title": "Reminder", "message": "Check your task"},
            token=self.token,
        )
        result = json.loads(response.read())
        self.assertEqual(response.status, 202)
        self.assertEqual(self.queue.list_jobs()[0]["kind"], "notification")
        self.assertEqual(self.queue.list_jobs()[0]["status"], "pending")
        self.assertEqual(result["job_id"], self.queue.list_jobs()[0]["id"])

    def test_rejects_extra_payload_fields_and_invalid_delay(self):
        for payload in (
            {"title": "x", "message": "y", "command": "rm -rf"},
            {"title": "x", "message": "y", "after_seconds": True},
            {"title": "", "message": "y"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(HTTPError) as caught:
                    self.request(
                        "/v1/notifications", method="POST",
                        payload=payload, token=self.token,
                    )
                self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.queue.list_jobs(), [])

    def test_job_listing_does_not_expose_result_or_error_details(self):
        self.queue.enqueue("notification", {"title": "private", "content": "private"})
        response = self.request("/v1/jobs?limit=5", token=self.token)
        item = json.loads(response.read())["jobs"][0]
        self.assertEqual(item["kind"], "notification")
        self.assertNotIn("result", item)
        self.assertNotIn("last_error", item)
        self.assertNotIn("payload", item)

    def test_rejects_non_loopback_host_and_weak_token(self):
        with self.assertRaisesRegex(ValueError, "32 characters"):
            make_handler("short", self.queue)
        with self.assertRaisesRegex(ValueError, "127.0.0.1"):
            serve("0.0.0.0", 8765, self.token, self.queue)

    def test_unknown_routes_are_not_exposed(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/v1/execute", token=self.token)
        self.assertEqual(caught.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
