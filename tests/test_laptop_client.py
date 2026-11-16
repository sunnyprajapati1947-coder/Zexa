from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from zexa.laptop_client import LaptopAgentClient, PairingCredentialStore
from zexa.laptop_pairing import LaptopPairingAuthority


class LaptopClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = PairingCredentialStore(Path(self.temp.name) / "phone" / "pairings.json")
        self.monotonic_now = 100.0
        self.wall_now = 1_800_000_000.0
        self.authority = LaptopPairingAuthority(
            iterations=100_000,
            monotonic=lambda: self.monotonic_now,
            wall_clock=time.time,
        )
        self.offer = self.authority.begin_pairing()

    def tearDown(self):
        self.temp.cleanup()

    def make_client(self):
        return LaptopAgentClient(
            "127.0.0.1", 9443, "a" * 64, "phone-main", store=self.store
        )

    def test_pairing_client_and_authenticated_workspace_requests(self):
        client = self.make_client()

        def fake_request(method, path, body=b"", headers=None):
            if method == "GET" and path == "/v1/pair/offer":
                return 200, {"ok": True, "offer": self.authority.public_offer()}
            if method == "POST" and path == "/v1/pair/complete":
                payload = json.loads(body.decode("utf-8"))
                record = self.authority.complete_pairing(
                    payload["client_id"], payload["client_nonce_b64"], payload["client_proof_b64"]
                )
                return 200, {
                    "ok": True,
                    "client_id": record.client_id,
                    "permissions": list(record.permissions),
                    "paired_at_epoch": record.paired_at_epoch,
                }
            if method == "POST" and path == "/v1/pair/revoke":
                self.assertTrue(self.authority.verify_scoped_request(
                    "phone-main", "laptop.workspace.list", method, path, b"", headers
                ))
                return 200, {"ok": True, "revoked": self.authority.revoke_client("phone-main")}
            if method == "GET" and path.startswith("/v1/workspace/list?"):
                self.assertTrue(self.authority.verify_scoped_request(
                    "phone-main", "laptop.workspace.list", method, path, b"", headers
                ))
                return 200, {"ok": True, "result": {"entries": [], "relative_dir": ".", "truncated": False}}
            if method == "GET" and path.startswith("/v1/workspace/read?"):
                self.assertTrue(self.authority.verify_scoped_request(
                    "phone-main", "laptop.workspace.read", method, path, b"", headers
                ))
                return 200, {"ok": True, "result": {"content": "hello"}}
            raise AssertionError(f"Unexpected request: {method} {path}")

        client._request = fake_request
        paired = client.pair(self.offer.pairing_code)
        self.assertEqual(paired["client_id"], "phone-main")
        self.assertIsNotNone(self.store.get("127.0.0.1", 9443, "phone-main"))
        self.assertEqual(client.list_directory()["entries"], [])
        self.assertEqual(client.read_text("lesson.txt")["content"], "hello")
        self.assertTrue(client.revoke_pairing())
        self.assertIsNone(self.store.get("127.0.0.1", 9443, "phone-main"))

    def test_existing_pairing_supplies_saved_tls_fingerprint(self):
        self.store.save(
            "127.0.0.1", 9443, "b" * 64, "phone-main",
            "A" * 43, ("laptop.workspace.read",),
        )
        client = LaptopAgentClient(
            "127.0.0.1", 9443, None, "phone-main", store=self.store
        )
        self.assertEqual(client.fingerprint, "b" * 64)
        with self.assertRaises(PermissionError):
            LaptopAgentClient(
                "127.0.0.1", 9443, None, "missing-client", store=self.store
            )

    def test_client_requires_fresh_confirmation_for_opt_in_remote_write(self):
        self.offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write"
        ))
        client = self.make_client()

        def fake_request(method, path, body=b"", headers=None):
            if method == "GET" and path == "/v1/pair/offer":
                return 200, {"ok": True, "offer": self.authority.public_offer()}
            if method == "POST" and path == "/v1/pair/complete":
                payload = json.loads(body.decode("utf-8"))
                record = self.authority.complete_pairing(
                    payload["client_id"], payload["client_nonce_b64"], payload["client_proof_b64"]
                )
                return 200, {
                    "ok": True, "client_id": record.client_id,
                    "permissions": list(record.permissions),
                    "paired_at_epoch": record.paired_at_epoch,
                }
            if method == "POST" and path == "/v1/workspace/write":
                self.assertTrue(self.authority.verify_scoped_request(
                    "phone-main", "laptop.workspace.write", method, path, body, headers
                ))
                payload = json.loads(body.decode("utf-8"))
                return 200, {"ok": True, "result": {
                    "relative_path": payload["relative_path"],
                    "written": True, "size_bytes": len(payload["content"]),
                    "sha256": "a" * 64,
                }}
            raise AssertionError(f"Unexpected request: {method} {path}")

        client._request = fake_request
        client.pair(self.offer.pairing_code)
        with self.assertRaises(PermissionError):
            client.write_text("notes.md", "content")
        with self.assertRaises(ValueError):
            client.write_text("notes.md", "bad\x00text", user_confirmed=True)
        result = client.write_text("notes.md", "content", user_confirmed=True)
        self.assertTrue(result["written"])

    def test_app_launch_requires_exact_permission_and_fresh_confirmation(self):
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-main",
            "A" * 43, ("laptop.apps.launch",),
        )
        client = self.make_client()
        calls = []

        def fake_request(method, path, body=b"", headers=None):
            calls.append((method, path, json.loads(body.decode("utf-8"))))
            return 200, {"ok": True, "result": {"app_id": "editor", "spawned": True}}

        client._request = fake_request
        with self.assertRaises(PermissionError):
            client.launch_app("editor")
        self.assertEqual(calls, [])
        result = client.launch_app("editor", user_confirmed=True)
        self.assertTrue(result["spawned"])
        self.assertEqual(calls[0], ("POST", "/v1/apps/launch", {"app_id": "editor"}))

    def test_app_inventory_requires_scope_and_validates_response(self):
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-main",
            "A" * 43, ("laptop.apps.launch",),
        )
        client = self.make_client()
        calls = []

        def fake_request(method, path, body=b"", headers=None):
            calls.append((method, path))
            self.assertTrue(LaptopPairingAuthority.verify_scoped_request(
                "phone-main", "laptop.apps.launch", method, path, body, headers
            ) is False or headers is not None)
            return 200, {"ok": True, "result": {"apps": [
                {"app_id": "editor", "description": "Approved editor"}
            ]}}

        client._request = fake_request
        self.assertEqual(client.list_apps(), [
            {"app_id": "editor", "description": "Approved editor"}
        ])
        self.assertEqual(calls, [("GET", "/v1/apps")])

        client._request = lambda *args, **kwargs: (
            200, {"ok": True, "result": {"apps": [
                {"app_id": "editor", "description": "ok", "executable": "/tmp/x"}
            ]}}
        )
        with self.assertRaises(RuntimeError):
            client.list_apps()

    def test_app_inventory_rejects_pairing_without_launch_permission(self):
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-main",
            "A" * 43, ("laptop.workspace.read",),
        )
        with self.assertRaises(PermissionError):
            self.make_client().list_apps()

    def test_app_launch_rejects_pairing_without_launch_permission(self):
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-main",
            "A" * 43, ("laptop.workspace.read",),
        )
        with self.assertRaises(PermissionError):
            self.make_client().launch_app("editor", user_confirmed=True)

    def test_client_rejects_public_or_hostname_targets(self):
        for host in ("example.com", "8.8.8.8", "0.0.0.0"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                LaptopAgentClient(host, 9443, "a" * 64, "phone-main")

    def test_credential_store_rejects_symlinked_secret_and_parent(self):
        if os.name == "nt":
            self.skipTest("Symlink creation requires platform-specific Windows privileges.")
        root = Path(self.temp.name)
        actual = root / "actual.json"
        actual.write_text('{"version":1,"pairs":[]}', encoding="utf-8")
        secret_link = root / "secret-link.json"
        secret_link.symlink_to(actual)
        with self.assertRaises(PermissionError):
            PairingCredentialStore(secret_link).get("127.0.0.1", 9443, "phone-main")

        real_dir = root / "real"
        real_dir.mkdir()
        parent_link = root / "linked-parent"
        parent_link.symlink_to(real_dir, target_is_directory=True)
        linked_store = PairingCredentialStore(parent_link / "pairings.json")
        linked_store.path.parent.mkdir(exist_ok=True)
        (parent_link / "pairings.json").write_text('{"version":1,"pairs":[]}', encoding="utf-8")
        with self.assertRaises(PermissionError):
            linked_store.get("127.0.0.1", 9443, "phone-main")

    def test_credential_store_rejects_world_readable_secret_file(self):
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-main",
            "A" * 43, ("laptop.workspace.read",),
        )
        if os.name != "nt":
            self.store.path.chmod(0o644)
            with self.assertRaises(PermissionError):
                self.store.get("127.0.0.1", 9443, "phone-main")

    def test_credential_store_rejects_unknown_permission_and_invalid_key(self):
        with self.assertRaises(ValueError):
            self.store.save(
                "127.0.0.1", 9443, "a" * 64, "phone-main",
                "A" * 43, ("shell.execute",),
            )
        self.store.save(
            "127.0.0.1", 9443, "a" * 64, "phone-editor",
            "A" * 43, ("laptop.workspace.write",),
        )
        with self.assertRaises(ValueError):
            self.store.save(
                "127.0.0.1", 9443, "a" * 64, "phone-main",
                "bad-key", ("laptop.workspace.read",),
            )


if __name__ == "__main__":
    unittest.main()
