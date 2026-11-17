from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from zexa.audit import AuditLog
from zexa.laptop_hand import LaptopWorkspace
from zexa.http_deadline import DeadlineSocketReader
from zexa.laptop_apps import LaptopAppRegistry
from zexa.laptop_pairing import LaptopPairingAuthority
from zexa.laptop_server import (
    LaptopAgentServer, _LaptopHTTPServer, make_laptop_handler,
    generate_laptop_certificate,
)


def encoded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class LaptopServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.root.mkdir()
        (self.root / "lesson.txt").write_text("hello laptop", encoding="utf-8")
        self.workspace = LaptopWorkspace(self.root)
        self.authority = LaptopPairingAuthority(iterations=100_000)
        self.offer = self.authority.begin_pairing()
        self.server = _LaptopHTTPServer(
            ("127.0.0.1", 0), make_laptop_handler(), self.workspace, self.authority,
            AuditLog(Path(self.temp.name) / "laptop_audit.sqlite3"),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, body=b"", headers=None):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8"))
        finally:
            connection.close()

    def pair(self, offer=None):
        offer = offer or self.offer
        nonce = encoded(bytes(range(32)))
        proof, session_key = LaptopPairingAuthority.make_client_proof(
            offer.pairing_code,
            offer.salt_b64,
            offer.server_nonce_b64,
            "phone-main",
            nonce,
            iterations=offer.iterations,
            permissions=offer.permissions,
        )
        body = json.dumps({
            "client_id": "phone-main",
            "client_nonce_b64": nonce,
            "client_proof_b64": proof,
        }).encode("utf-8")
        status, result = self.request(
            "POST", "/v1/pair/complete", body,
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        self.assertEqual(status, 200)
        return session_key

    def signed(self, session_key, method, path):
        headers = LaptopPairingAuthority.sign_request(session_key, method, path, b"")
        headers["X-Zexa-Client-ID"] = "phone-main"
        return headers

    def test_server_closes_slow_request_line_at_total_deadline(self):
        stop = threading.Event()

        def trickle(connection):
            try:
                while not stop.is_set():
                    connection.sendall(b"G")
                    time.sleep(0.04)
            except OSError:
                pass

        # Patch before connect: the server may accept and construct its
        # handler immediately after the TCP handshake completes.
        with patch("zexa.laptop_server.REQUEST_READ_TIMEOUT_SECONDS", 0.2):
            connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
            connection.settimeout(1.0)
            sender = threading.Thread(target=trickle, args=(connection,), daemon=True)
            sender.start()
            started = time.monotonic()
            try:
                while connection.recv(1024):
                    pass
                self.assertLess(time.monotonic() - started, 0.8)
            finally:
                stop.set()
                connection.close()
                sender.join(timeout=1)

        # The timed-out request must release its bounded worker slot.
        status, _ = self.request("GET", "/v1/pair/offer")
        self.assertEqual(status, 200)

    def test_rejects_duplicate_content_length_headers(self):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.putrequest("POST", "/v1/pair/complete")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", "2")
            connection.putheader("Content-Length", "2")
            connection.endheaders(b"{}")
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            self.assertIn("Content-Length", response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_rejects_non_decimal_content_length_values(self):
        for invalid_length in ("+2", "2_0", "-2", "0x2", "2e0"):
            with self.subTest(content_length=invalid_length):
                connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
                try:
                    connection.putrequest("POST", "/v1/pair/complete")
                    connection.putheader("Content-Type", "application/json")
                    connection.putheader("Content-Length", invalid_length)
                    connection.endheaders(b"{}")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 400)
                    self.assertIn("Content-Length", response.read().decode("utf-8"))
                finally:
                    connection.close()

    def test_rejects_non_ascii_content_length_bytes(self):
        import socket

        connection = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        try:
            connection.sendall(
                b"POST /v1/pair/complete HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: \xff\r\n"
                b"Connection: close\r\n\r\n{}"
            )
            response = connection.makefile("rb").readline()
            self.assertIn(b"400", response)
        finally:
            connection.close()

    def test_rejects_duplicate_content_type_headers(self):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            connection.putrequest("POST", "/v1/pair/complete")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Type", "application/json")
            connection.putheader("Content-Length", "2")
            connection.endheaders(b"{}")
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            self.assertIn("Content-Type", response.read().decode("utf-8"))
        finally:
            connection.close()

    def test_pair_offer_never_exposes_one_time_code(self):
        status, result = self.request("GET", "/v1/pair/offer")
        self.assertEqual(status, 200)
        self.assertNotIn("pairing_code", result["offer"])
        self.assertEqual(result["offer"]["permissions"], list(self.offer.permissions))

    def test_paired_client_can_list_and_read_only_with_scoped_mac(self):
        key = self.pair()
        list_path = "/v1/workspace/list?" + urlencode({"dir": "."})
        status, listing = self.request("GET", list_path, headers=self.signed(key, "GET", list_path))
        self.assertEqual(status, 200)
        self.assertEqual(listing["result"]["entries"][0]["name"], "lesson.txt")

        read_path = "/v1/workspace/read?" + urlencode({"path": "lesson.txt"})
        status, result = self.request("GET", read_path, headers=self.signed(key, "GET", read_path))
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["content"], "hello laptop")

    def test_workspace_read_requires_valid_mac_and_scope(self):
        self.pair()
        path = "/v1/workspace/read?" + urlencode({"path": "lesson.txt"})
        status, result = self.request("GET", path)
        self.assertEqual(status, 401)
        self.assertEqual(result["error"], "unauthorized_or_scope_denied")

    def test_remote_write_requires_opt_in_pairing_scope(self):
        key = self.pair()
        path = "/v1/workspace/write"
        body = json.dumps({
            "relative_path": "new.md", "content": "new content", "overwrite": False
        }, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        status, _ = self.request("POST", path, body, headers)
        self.assertEqual(status, 401)
        self.assertFalse((self.root / "new.md").exists())

    def test_explicitly_paired_write_scope_can_create_and_replace_workspace_text(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write"
        ))
        key = self.pair(offer)
        path = "/v1/workspace/write"
        body = json.dumps({
            "relative_path": "new.md", "content": "first", "overwrite": False
        }, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        status, result = self.request("POST", path, body, headers)
        self.assertEqual(status, 200)
        self.assertTrue(result["result"]["written"])
        self.assertEqual((self.root / "new.md").read_text(encoding="utf-8"), "first")

        body = json.dumps({
            "relative_path": "new.md", "content": "second", "overwrite": False
        }, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        status, _ = self.request("POST", path, body, headers)
        self.assertEqual(status, 409)

    def test_app_launch_requires_opt_in_pairing_scope_and_owner_allowlist(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.apps.launch"
        ))
        key = self.pair(offer)
        manifest = Path(self.temp.name) / "apps.json"
        executable = Path(self.temp.name) / "python-executable"
        shutil.copy2(Path(sys.executable).resolve(), executable)
        executable.chmod(stat.S_IMODE(executable.stat().st_mode) & ~0o022)
        manifest.write_text(json.dumps({
            "version": 1,
            "apps": [{
                "id": "python-tool",
                "executable": str(executable),
                "arguments": ["--version"],
                "description": "Python version tool",
            }],
        }), encoding="utf-8")
        self.server.app_registry = LaptopAppRegistry(manifest)
        path = "/v1/apps/launch"
        body = json.dumps({"app_id": "python-tool"}, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        with patch("zexa.laptop_apps.subprocess.Popen") as spawn:
            spawn.return_value.pid = 4321
            status, result = self.request("POST", path, body, headers)
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["app_id"], "python-tool")
        spawn.assert_called_once()
        self.assertIs(spawn.call_args.kwargs["shell"], False)

    def test_app_inventory_requires_pairing_scope_and_returns_only_allowlisted_metadata(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.apps.launch"
        ))
        key = self.pair(offer)
        manifest = Path(self.temp.name) / "apps-list.json"
        executable = Path(self.temp.name) / "python-list-executable"
        shutil.copy2(Path(sys.executable).resolve(), executable)
        executable.chmod(stat.S_IMODE(executable.stat().st_mode) & ~0o022)
        manifest.write_text(json.dumps({
            "version": 1,
            "apps": [{
                "id": "editor",
                "executable": str(executable),
                "arguments": [],
                "description": "Approved text editor",
            }],
        }), encoding="utf-8")
        self.server.app_registry = LaptopAppRegistry(manifest)
        path = "/v1/apps"
        status, _ = self.request("GET", path)
        self.assertEqual(status, 401)
        status, result = self.request("GET", path, headers=self.signed(key, "GET", path))
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["apps"], [{
            "app_id": "editor", "description": "Approved text editor"
        }])
        self.assertNotIn("executable", json.dumps(result))
        self.assertNotIn("arguments", json.dumps(result))

    def test_app_launch_denied_without_explicit_pairing_scope(self):
        key = self.pair()
        path = "/v1/apps/launch"
        body = json.dumps({"app_id": "editor"}).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        with patch("zexa.laptop_apps.subprocess.Popen") as spawn:
            status, _ = self.request("POST", path, body, headers)
        self.assertEqual(status, 401)
        spawn.assert_not_called()

    def test_exact_confirmed_browser_navigation_opens_visible_default_browser(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.browser.open"
        ))
        key = self.pair(offer)
        path = "/v1/browser/open"
        url = "https://example.com/docs?topic=zexa"
        body = json.dumps({"url": url}, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        with patch("zexa.laptop_browser.webbrowser.open", return_value=True) as open_browser:
            status, result = self.request("POST", path, body, headers)
        self.assertEqual(status, 200)
        self.assertEqual(result["result"], {"opened": True, "host": "example.com"})
        open_browser.assert_called_once_with(url, new=2, autoraise=True)
        events = self.server.audit.recent(10)
        event = next(item for item in events if item["event_type"] == "laptop_browser_navigation")
        self.assertEqual(event["details"], {"host": "example.com"})
        self.assertNotIn("topic=zexa", json.dumps(event["details"]))

    def test_browser_navigation_denied_without_opt_in_scope(self):
        key = self.pair()
        path = "/v1/browser/open"
        body = json.dumps({"url": "https://example.com"}, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        with patch("zexa.laptop_browser.webbrowser.open") as open_browser:
            status, _ = self.request("POST", path, body, headers)
        self.assertEqual(status, 401)
        open_browser.assert_not_called()

    def test_browser_navigation_rejects_non_https_destinations(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.browser.open"
        ))
        key = self.pair(offer)
        path = "/v1/browser/open"
        body = json.dumps({"url": "http://example.com"}, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(key, "POST", path, body)
        headers.update({
            "X-Zexa-Client-ID": "phone-main",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        with patch("zexa.laptop_browser.webbrowser.open") as open_browser:
            status, _ = self.request("POST", path, body, headers)
        self.assertEqual(status, 400)
        open_browser.assert_not_called()

    def test_scoped_public_page_read_returns_text_and_audits_only_metadata(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.browser.read"
        ))
        key = self.pair(offer)
        path = "/v1/browser/read?" + urlencode({"url": "https://example.com/article"})
        page = {
            "title": "Example article",
            "url": "https://example.com/article",
            "text": "Public article text with an instruction-like phrase.",
            "content_sha256": "a" * 64,
        }
        with patch("zexa.laptop_server.read_public_page", return_value=page) as read_page:
            status, result = self.request("GET", path, headers=self.signed(key, "GET", path))
        self.assertEqual(status, 200)
        self.assertEqual(result["result"], page)
        read_page.assert_called_once_with("https://example.com/article")
        event = next(
            item for item in self.server.audit.recent(10)
            if item["event_type"] == "laptop_browser_read"
        )
        self.assertEqual(event["details"], {
            "host": "example.com", "size_chars": len(page["text"]),
            "content_sha256": "a" * 64,
        })
        self.assertNotIn(page["text"], json.dumps(event["details"]))

    def test_public_page_read_requires_separate_opt_in_scope(self):
        key = self.pair()
        path = "/v1/browser/read?" + urlencode({"url": "https://example.com"})
        with patch("zexa.laptop_server.read_public_page") as read_page:
            status, _ = self.request("GET", path, headers=self.signed(key, "GET", path))
        self.assertEqual(status, 401)
        read_page.assert_not_called()

    def test_public_page_read_rejects_ambiguous_query(self):
        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.browser.read"
        ))
        key = self.pair(offer)
        path = "/v1/browser/read?url=https%3A%2F%2Fexample.com&extra=1"
        with patch("zexa.laptop_server.read_public_page") as read_page:
            status, _ = self.request("GET", path, headers=self.signed(key, "GET", path))
        self.assertEqual(status, 400)
        read_page.assert_not_called()

    def test_remote_shell_route_is_not_exposed(self):
        self.pair()
        status, _ = self.request("POST", "/v1/shell", b"{}")
        self.assertEqual(status, 404)

    def test_paired_client_can_revoke_its_own_access(self):
        key = self.pair()
        revoke_path = "/v1/pair/revoke"
        status, result = self.request(
            "POST", revoke_path, headers=self.signed(key, "POST", revoke_path)
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["revoked"])
        list_path = "/v1/workspace/list?" + urlencode({"dir": "."})
        status, _ = self.request(
            "GET", list_path, headers=self.signed(key, "GET", list_path)
        )
        self.assertEqual(status, 401)

    def test_pairing_offer_is_single_use(self):
        self.pair()
        status, result = self.request("GET", "/v1/pair/offer")
        self.assertEqual(status, 404)
        self.assertEqual(result["error"], "no_active_pairing_offer")

    def test_certificate_generation_uses_fixed_openssl_arguments_and_private_key_mode(self):
        cert = Path(self.temp.name) / "generated.crt"
        key = Path(self.temp.name) / "generated.key"
        der = b"test certificate DER"
        pem = (
            "-----BEGIN CERTIFICATE-----\n"
            + base64.b64encode(der).decode("ascii")
            + "\n-----END CERTIFICATE-----\n"
        )

        def fake_run(command, **kwargs):
            self.assertNotIn("shell", kwargs)
            Path(command[command.index("-keyout") + 1]).write_text("private-key", encoding="ascii")
            Path(command[command.index("-out") + 1]).write_text(pem, encoding="ascii")

        with patch("zexa.laptop_server.shutil.which", return_value="/usr/bin/openssl"):
            with patch("zexa.laptop_server.subprocess.run", side_effect=fake_run):
                fingerprint = generate_laptop_certificate("192.168.1.20", cert, key)

        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(cert.is_file())
        self.assertTrue(key.is_file())
        if os.name != "nt":
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)

    def test_certificate_generation_refuses_overwrite_and_public_ip(self):
        cert = Path(self.temp.name) / "existing.crt"
        key = Path(self.temp.name) / "existing.key"
        cert.write_text("existing", encoding="ascii")
        with patch("zexa.laptop_server.shutil.which", return_value="/usr/bin/openssl"):
            with self.assertRaises(FileExistsError):
                generate_laptop_certificate("192.168.1.20", cert, key)
            with self.assertRaises(ValueError):
                generate_laptop_certificate("8.8.8.8", cert, key)

    def test_workspace_actions_are_audited_without_recording_file_contents(self):
        key = self.pair()
        read_path = "/v1/workspace/read?" + urlencode({"path": "lesson.txt"})
        status, _ = self.request(
            "GET", read_path, headers=self.signed(key, "GET", read_path)
        )
        self.assertEqual(status, 200)
        events = self.server.audit.recent(10)
        read_event = next(item for item in events if item["event_type"] == "laptop_workspace_read")
        self.assertEqual(read_event["details"]["relative_path"], "lesson.txt")
        self.assertNotIn("hello laptop", json.dumps(read_event["details"]))

    def test_client_can_revoke_pairing_without_workspace_list_scope(self):
        offer = self.authority.begin_pairing(permissions=("laptop.browser.read",))
        key = self.pair(offer)
        revoke_path = "/v1/pair/revoke"
        status, result = self.request(
            "POST", revoke_path, headers=self.signed(key, "POST", revoke_path)
        )
        self.assertEqual(status, 200)
        self.assertTrue(result["revoked"])
        self.assertEqual(self.authority.list_clients(), [])

    def test_agent_server_rejects_wildcard_and_public_bind_addresses(self):
        for host in ("0.0.0.0", "8.8.8.8", "example.com"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                LaptopAgentServer(host, 9443, "missing.crt", "missing.key", self.workspace)


class DeadlineSocketReaderTests(unittest.TestCase):
    def _assert_slow_trickle_expires(self, read_operation):
        receiver, sender = socket.socketpair()
        reader = DeadlineSocketReader(receiver, request_timeout=0.2, idle_timeout=1.0)
        stop = threading.Event()

        def trickle():
            try:
                while not stop.is_set():
                    sender.sendall(b"x")
                    time.sleep(0.04)
            except OSError:
                pass

        thread = threading.Thread(target=trickle, daemon=True)
        thread.start()
        started = time.monotonic()
        reader.begin_request()
        try:
            with self.assertRaises(socket.timeout):
                read_operation(reader)
            self.assertTrue(reader.timed_out)
            self.assertLess(time.monotonic() - started, 0.8)
        finally:
            reader.end_request()
            reader.close()
            stop.set()
            sender.close()
            receiver.close()
            thread.join(timeout=1)

    def test_request_line_slow_trickle_uses_one_total_deadline(self):
        self._assert_slow_trickle_expires(lambda reader: reader.readline(4096))

    def test_request_body_slow_trickle_uses_one_total_deadline(self):
        self._assert_slow_trickle_expires(lambda reader: reader.read(64))


if __name__ == "__main__":
    unittest.main()
