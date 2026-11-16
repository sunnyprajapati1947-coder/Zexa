from __future__ import annotations

import base64
import json
import os
from unittest.mock import patch
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlencode

from zexa.laptop_hand import LaptopWorkspace
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
            ("127.0.0.1", 0), make_laptop_handler(), self.workspace, self.authority
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

    def pair(self):
        nonce = encoded(bytes(range(32)))
        proof, session_key = LaptopPairingAuthority.make_client_proof(
            self.offer.pairing_code,
            self.offer.salt_b64,
            self.offer.server_nonce_b64,
            "phone-main",
            nonce,
            iterations=self.offer.iterations,
            permissions=self.offer.permissions,
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

    def test_remote_write_and_shell_routes_are_not_exposed(self):
        self.pair()
        status, _ = self.request("POST", "/v1/workspace/write", b"{}")
        self.assertEqual(status, 404)
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
            "-----BEGIN CERTIFICATE-----\\n"
            + base64.b64encode(der).decode("ascii")
            + "\\n-----END CERTIFICATE-----\\n"
        )

        def fake_run(command, **kwargs):
            self.assertNotIn("shell", kwargs)
            Path(command[command.index("-keyout") + 1]).write_text("private-key", encoding="ascii")
            Path(command[command.index("-out") + 1]).write_text(pem, encoding="ascii")

        with patch("zexa.laptop_server.shutil.which", return_value="/usr/bin/openssl"):
            with patch("zexa.laptop_server.subprocess.run", side_effect=fake_run):
                fingerprint = generate_laptop_certificate("192.168.1.20", cert, key)
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

    def test_agent_server_rejects_wildcard_and_public_bind_addresses(self):
        for host in ("0.0.0.0", "8.8.8.8", "example.com"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                LaptopAgentServer(host, 9443, "missing.crt", "missing.key", self.workspace)


if __name__ == "__main__":
    unittest.main()
