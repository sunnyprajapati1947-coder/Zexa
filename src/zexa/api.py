"""Authenticated loopback-only HTTP control surface for safe Zexa operations."""
from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Type

from .jobs import JobQueue


MAX_BODY = 4096


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def make_handler(token: str, queue: JobQueue) -> Type[BaseHTTPRequestHandler]:
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("ZEXA_API_TOKEN must contain at least 32 characters.")

    class Handler(BaseHTTPRequestHandler):
        server_version = "ZexaLocalAPI"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            # Avoid writing request headers, tokens, or user content to shared logs.
            return

        def _send(self, status: int, payload: object) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            supplied = self.headers.get("Authorization", "")
            prefix = "Bearer "
            candidate = supplied[len(prefix):] if supplied.startswith(prefix) else ""
            if not hmac.compare_digest(candidate, token):
                self._send(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self) -> None:
            if not self._authorized():
                return
            if self.path == "/v1/health":
                self._send(200, {"ok": True, "service": "zexa"})
                return
            if self.path == "/v1/jobs":
                try:
                    limit = int(self.headers.get("X-Zexa-Limit", "20"))
                    if not 1 <= limit <= 50:
                        raise ValueError
                except ValueError:
                    self._send(400, {"error": "invalid_limit"})
                    return
                self._send(200, {"jobs": queue.list_jobs(limit)})
                return
            self._send(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self._authorized():
                return
            if self.path != "/v1/notifications":
                self._send(404, {"error": "not_found"})
                return
            raw_length = self.headers.get("Content-Length", "")
            try:
                length = int(raw_length)
            except ValueError:
                self._send(411, {"error": "content_length_required"})
                return
            if not 1 <= length <= MAX_BODY:
                self._send(413, {"error": "body_too_large_or_empty"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._send(415, {"error": "application_json_required"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send(400, {"error": "invalid_json"})
                return
            if not isinstance(payload, dict) or set(payload) - {"title", "message", "after_seconds"}:
                self._send(400, {"error": "invalid_payload"})
                return
            title, message = payload.get("title"), payload.get("message")
            delay = payload.get("after_seconds", 0)
            if (not isinstance(title, str) or not title.strip() or len(title) > 120
                    or not isinstance(message, str) or not message.strip() or len(message) > 1000
                    or type(delay) is not int or not 0 <= delay <= 604800):
                self._send(400, {"error": "invalid_payload"})
                return
            from datetime import datetime, timedelta, timezone
            run_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            job_id = queue.enqueue(
                "notification",
                {"title": title.strip(), "content": message.strip()},
                run_at=run_at,
            )
            self._send(202, {"queued": True, "job_id": job_id})

    return Handler


def serve(host: str, port: int, token: str, queue: JobQueue | None = None) -> None:
    """Serve only on IPv4 loopback; remote/LAN binds are rejected."""
    if host != "127.0.0.1":
        raise ValueError("Zexa API may bind only to 127.0.0.1.")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("API port must be between 1024 and 65535.")
    job_queue = queue or JobQueue()
    server = ThreadingHTTPServer((host, port), make_handler(token, job_queue))
    server.daemon_threads = True
    print(f"Zexa local API listening on http://{host}:{port}. Press Ctrl+C to stop.")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nZexa local API stopped.")
    finally:
        server.server_close()
