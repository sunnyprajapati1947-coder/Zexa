from __future__ import annotations

import base64
import hashlib
import unittest

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
