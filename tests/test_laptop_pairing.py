from __future__ import annotations

import base64
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from zexa.laptop_pairing import LaptopPairingAuthority, verify_tls_fingerprint


def encoded(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


class LaptopPairingTests(unittest.TestCase):
    def setUp(self):
        self.monotonic_now = 100.0
        self.wall_now = 1_800_000_000.0
        self.authority = LaptopPairingAuthority(
            ttl_seconds=60,
            max_attempts=3,
            iterations=100_000,
            monotonic=lambda: self.monotonic_now,
            wall_clock=lambda: self.wall_now,
        )

    def make_pair(self, client_id="phone-main"):
        offer = self.authority.begin_pairing()
        client_nonce = encoded(bytes(range(32)))
        proof, session_key = self.authority.make_client_proof(
            offer.pairing_code,
            offer.salt_b64,
            offer.server_nonce_b64,
            client_id,
            client_nonce,
            iterations=offer.iterations,
            permissions=offer.permissions,
        )
        record = self.authority.complete_pairing(client_id, client_nonce, proof)
        return offer, record, session_key

    def test_one_time_code_pairing_derives_same_session_key(self):
        offer, record, session_key = self.make_pair()
        self.assertRegex(offer.pairing_code, r"^\d{12}$")
        self.assertEqual(encoded(record.session_key), session_key)
        self.assertEqual(self.authority.list_clients(), [{
            "client_id": "phone-main",
            "paired_at_epoch": int(self.wall_now),
            "permissions": ["laptop.workspace.list", "laptop.workspace.read"],
        }])
        with self.assertRaises(PermissionError):
            self.authority.complete_pairing("phone-main", encoded(bytes(32)), encoded(bytes(32)))

    def test_revoke_all_clients_clears_sessions_and_replay_state(self):
        self.make_pair("phone-main")
        self.make_pair("phone-secondary")
        self.assertEqual(len(self.authority.list_clients()), 2)
        self.assertEqual(self.authority.revoke_all_clients(), 2)
        self.assertEqual(self.authority.list_clients(), [])
        self.assertFalse(self.authority.verify_request(
            "phone-main", "GET", "/v1/workspace/list", b"", {},
        ))
        self.assertEqual(self.authority.revoke_all_clients(), 0)

    def test_pairing_binds_requested_permissions_and_defaults_to_read_only(self):
        _, read_only, key = self.make_pair()
        self.assertTrue(read_only.allows("laptop.workspace.read"))
        self.assertFalse(read_only.allows("laptop.workspace.write"))
        headers = self.authority.sign_request(
            key, "POST", "/v1/workspace/write", b"data",
            timestamp=int(self.wall_now), nonce_b64=encoded(b"w" * 24),
        )
        self.assertFalse(self.authority.verify_scoped_request(
            "phone-main", "laptop.workspace.write", "POST",
            "/v1/workspace/write", b"data", headers,
        ))

        self.assertEqual(read_only.permissions, (
            "laptop.workspace.list", "laptop.workspace.read"
        ))

        offer = self.authority.begin_pairing(permissions=(
            "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write"
        ))
        client_nonce = encoded(b"z" * 32)
        proof, session_key = self.authority.make_client_proof(
            offer.pairing_code, offer.salt_b64, offer.server_nonce_b64,
            "phone-editor", client_nonce, iterations=offer.iterations,
            permissions=offer.permissions,
        )
        paired = self.authority.complete_pairing("phone-editor", client_nonce, proof)
        self.assertEqual(encoded(paired.session_key), session_key)
        self.assertTrue(paired.allows("laptop.workspace.write"))

    def test_pairing_rejects_unknown_permission_scopes(self):
        with self.assertRaises(ValueError):
            self.authority.begin_pairing(permissions=("shell.execute",))

    def test_wrong_proofs_are_bounded_and_offer_is_invalidated(self):
        offer = self.authority.begin_pairing()
        nonce = encoded(bytes(range(32)))
        for _ in range(3):
            with self.assertRaises(PermissionError):
                self.authority.complete_pairing("phone-main", nonce, encoded(bytes(32)))
        with self.assertRaises(PermissionError):
            self.authority.complete_pairing("phone-main", nonce, encoded(bytes(32)))

    def test_pairing_offer_expires(self):
        offer = self.authority.begin_pairing()
        self.monotonic_now += 61
        with self.assertRaises(TimeoutError):
            self.authority.complete_pairing("phone-main", encoded(bytes(32)), encoded(bytes(32)))

    def test_pairing_rejects_invalid_client_ids(self):
        offer = self.authority.begin_pairing()
        with self.assertRaises(ValueError):
            self.authority.make_client_proof(
                offer.pairing_code, offer.salt_b64, offer.server_nonce_b64,
                "../bad-client", encoded(bytes(32)), iterations=offer.iterations,
            )

    def test_request_mac_is_bound_to_method_path_body_and_nonce(self):
        _, record, session_key = self.make_pair()
        body = b'{"relative_path":"notes.md"}'
        headers = self.authority.sign_request(
            session_key, "GET", "/v1/workspace/read", body,
            timestamp=int(self.wall_now), nonce_b64=encoded(b"n" * 24),
        )
        self.assertTrue(self.authority.verify_request(
            "phone-main", "GET", "/v1/workspace/read", body, headers
        ))
        self.assertFalse(self.authority.verify_request(
            "phone-main", "GET", "/v1/workspace/read", body, headers
        ))
        padded_nonce = dict(headers)
        padded_nonce["X-Zexa-Nonce"] += "=="
        self.assertFalse(self.authority.verify_request(
            "phone-main", "GET", "/v1/workspace/read", body, padded_nonce
        ))
        changed = dict(headers)
        changed["X-Zexa-Nonce"] = encoded(b"m" * 24)
        self.assertFalse(self.authority.verify_request(
            "phone-main", "POST", "/v1/workspace/read", body, changed
        ))

    def test_request_mac_rejects_stale_timestamps_and_oversized_bodies(self):
        _, _, session_key = self.make_pair()
        stale = self.authority.sign_request(
            session_key, "GET", "/v1/status", b"",
            timestamp=int(self.wall_now) - 60, nonce_b64=encoded(b"s" * 24),
        )
        self.assertFalse(self.authority.verify_request(
            "phone-main", "GET", "/v1/status", b"", stale
        ))
        with self.assertRaises(ValueError):
            self.authority.sign_request(
                session_key, "POST", "/v1/upload", b"x" * 1_000_001,
                timestamp=int(self.wall_now), nonce_b64=encoded(b"t" * 24),
            )

    def test_revocation_invalidates_request_authentication(self):
        _, _, session_key = self.make_pair()
        headers = self.authority.sign_request(
            session_key, "GET", "/v1/status", b"",
            timestamp=int(self.wall_now), nonce_b64=encoded(b"r" * 24),
        )
        self.assertTrue(self.authority.revoke_client("phone-main"))
        self.assertFalse(self.authority.verify_request(
            "phone-main", "GET", "/v1/status", b"", headers
        ))
        self.assertFalse(self.authority.revoke_client("phone-main"))

    def test_persistent_pairings_and_replay_nonces_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "pairings.sqlite3"
            first = LaptopPairingAuthority(
                iterations=100_000,
                wall_clock=lambda: self.wall_now,
                storage_path=database,
            )
            offer = first.begin_pairing()
            client_nonce = encoded(b"p" * 32)
            proof, session_key = first.make_client_proof(
                offer.pairing_code, offer.salt_b64, offer.server_nonce_b64,
                "phone-persist", client_nonce, iterations=offer.iterations,
                permissions=offer.permissions,
            )
            first.complete_pairing("phone-persist", client_nonce, proof)
            headers = first.sign_request(
                session_key, "GET", "/v1/workspace/list", b"",
                timestamp=int(self.wall_now), nonce_b64=encoded(b"q" * 24),
            )

            second = LaptopPairingAuthority(
                iterations=100_000,
                wall_clock=lambda: self.wall_now,
                storage_path=database,
            )
            self.assertEqual(second.list_clients()[0]["client_id"], "phone-persist")
            self.assertTrue(second.verify_request(
                "phone-persist", "GET", "/v1/workspace/list", b"", headers
            ))

            third = LaptopPairingAuthority(
                iterations=100_000,
                wall_clock=lambda: self.wall_now,
                storage_path=database,
            )
            self.assertFalse(third.verify_request(
                "phone-persist", "GET", "/v1/workspace/list", b"", headers
            ))
            revocation_probe = LaptopPairingAuthority.sign_request(
                session_key, "GET", "/v1/workspace/list", b"",
                timestamp=int(self.wall_now), nonce_b64=encoded(b"s" * 24),
            )
            self.assertTrue(third.revoke_client("phone-persist"))
            self.assertEqual(third.list_clients(), [])
            self.assertFalse(second.verify_request(
                "phone-persist", "GET", "/v1/workspace/list", b"", revocation_probe
            ))
            self.assertEqual(second.list_clients(), [])
            expanded_offer = third.begin_pairing(permissions=(
                "laptop.workspace.list", "laptop.workspace.read", "laptop.apps.launch"
            ))
            expanded_nonce = encoded(b"r" * 32)
            expanded_proof, expanded_session_key = third.make_client_proof(
                expanded_offer.pairing_code, expanded_offer.salt_b64,
                expanded_offer.server_nonce_b64, "phone-persist", expanded_nonce,
                iterations=expanded_offer.iterations, permissions=expanded_offer.permissions,
            )
            expanded_record = third.complete_pairing(
                "phone-persist", expanded_nonce, expanded_proof
            )
            self.assertIn("laptop.apps.launch", expanded_record.permissions)
            fourth = LaptopPairingAuthority(
                iterations=100_000,
                wall_clock=lambda: self.wall_now,
                storage_path=database,
            )
            self.assertEqual(fourth.list_clients()[0]["client_id"], "phone-persist")
            self.assertIn("laptop.apps.launch", fourth.list_clients()[0]["permissions"])
            expanded_probe = LaptopPairingAuthority.sign_request(
                expanded_session_key, "GET", "/v1/workspace/list", b"",
                timestamp=int(self.wall_now), nonce_b64=encoded(b"u" * 24),
            )
            self.assertTrue(second.verify_request(
                "phone-persist", "GET", "/v1/workspace/list", b"", expanded_probe
            ))
            if os.name != "nt":
                self.assertEqual(database.stat().st_mode & 0o777, 0o600)

    def test_persistent_pairing_database_rejects_symlink(self):
        if os.name == "nt":
            self.skipTest("Symlink permissions differ on Windows.")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target.sqlite3"
            target.touch()
            link = root / "pairings.sqlite3"
            link.symlink_to(target)
            with self.assertRaises(PermissionError):
                LaptopPairingAuthority(storage_path=link)

    def test_certificate_fingerprint_is_pinned(self):
        certificate = b"test-certificate-der"
        fingerprint = hashlib.sha256(certificate).hexdigest()
        self.assertTrue(verify_tls_fingerprint(certificate, fingerprint))
        self.assertTrue(verify_tls_fingerprint(certificate, ":".join(
            fingerprint[i:i + 2] for i in range(0, len(fingerprint), 2)
        )))
        self.assertFalse(verify_tls_fingerprint(certificate, "0" * 64))
        self.assertFalse(verify_tls_fingerprint(certificate, "not-a-fingerprint"))


if __name__ == "__main__":
    unittest.main()
