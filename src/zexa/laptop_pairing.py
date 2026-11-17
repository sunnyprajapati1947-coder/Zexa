"""Cryptographic primitives for an explicitly user-paired laptop Human Hand.

This module implements a one-time-code challenge, TLS certificate pin check,
and replay-resistant request MACs. It does not open sockets or start a remote
service. Callers must establish TLS and verify the displayed certificate
fingerprint out of band before sending any pairing message.
"""
from __future__ import annotations

import base64
from contextlib import closing
import csv
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import secrets
import shutil
import subprocess
import threading
import time
from typing import Callable


_CLIENT_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_MAX_BODY_BYTES = 1_000_000
_MAX_PATH_CHARS = 1024
_MAX_REPLAY_ENTRIES = 512
_ALLOWED_PERMISSIONS = frozenset({
    "laptop.workspace.list",
    "laptop.workspace.read",
    "laptop.workspace.write",
    "laptop.apps.launch",
    "laptop.browser.open",
    "laptop.browser.read",
})
_DEFAULT_PERMISSIONS = ("laptop.workspace.list", "laptop.workspace.read")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str, *, expected_bytes: int) -> bytes:
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise ValueError("Invalid encoded pairing value.")
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid encoded pairing value.") from exc
    if len(decoded) != expected_bytes:
        raise ValueError("Encoded pairing value has an invalid length.")
    return decoded


def secure_owner_only(path: str | Path, *, directory: bool = False) -> None:
    """Restrict a sensitive file or directory to its owner (plus Windows system admins)."""
    target = Path(path)
    if target.is_symlink():
        raise PermissionError("Sensitive Zexa storage must not be a symbolic link.")
    if os.name == "nt":
        icacls = shutil.which("icacls")
        whoami = shutil.which("whoami")
        if not icacls or not whoami:
            raise PermissionError("Windows icacls and whoami are required to secure Zexa pairing files.")
        try:
            identity = subprocess.run(
                [whoami, "/user", "/fo", "csv", "/nh"],
                check=False, capture_output=True, text=True, timeout=10,
            )
            rows = list(csv.reader(identity.stdout.splitlines()))
            user_sid = rows[0][1].strip() if identity.returncode == 0 and rows and len(rows[0]) >= 2 else ""
        except (OSError, subprocess.TimeoutExpired, csv.Error, IndexError) as exc:
            raise PermissionError("Could not identify the current Windows user SID.") from exc
        if not re.fullmatch(r"S-\d+(?:-\d+)+", user_sid):
            raise PermissionError("Windows did not return a valid current-user SID.")
        suffix = "(OI)(CI)F" if directory else "(F)"
        command = [
            icacls, str(target), "/inheritance:r",
            "/grant:r", f"*{user_sid}:{suffix}",
            "/grant:r", f"*S-1-5-18:{suffix}",
            "/grant:r", f"*S-1-5-32-544:{suffix}",
        ]
        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PermissionError("Could not apply a restricted Windows ACL to Zexa storage.") from exc
        if result.returncode != 0:
            raise PermissionError("Windows rejected the restricted Zexa storage ACL.")
    else:
        os.chmod(target, 0o700 if directory else 0o600)


def verify_tls_fingerprint(certificate_der: bytes, expected_sha256: str) -> bool:
    """Verify the peer's DER certificate against a fingerprint shown locally."""
    if not isinstance(certificate_der, bytes) or not certificate_der or len(certificate_der) > 64_000:
        return False
    if not isinstance(expected_sha256, str):
        return False
    normalized = expected_sha256.replace(":", "").strip().lower()
    if not _SHA256_HEX.fullmatch(normalized):
        return False
    actual = hashlib.sha256(certificate_der).hexdigest()
    return hmac.compare_digest(actual, normalized)


@dataclass(frozen=True)
class PairingOffer:
    pairing_code: str
    salt_b64: str
    server_nonce_b64: str
    expires_in_seconds: int
    iterations: int
    permissions: tuple[str, ...]


@dataclass(frozen=True)
class PairedLaptopClient:
    client_id: str
    session_key: bytes
    paired_at_epoch: int
    permissions: tuple[str, ...]

    def allows(self, permission: str) -> bool:
        return permission in self.permissions


class LaptopPairingAuthority:
    """Pairing authority with optional owner-only persistence and replay protection."""

    def __init__(
        self,
        *,
        ttl_seconds: int = 120,
        max_attempts: int = 5,
        iterations: int = 310_000,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        storage_path: str | Path | None = None,
    ) -> None:
        if type(ttl_seconds) is not int or not 30 <= ttl_seconds <= 300:
            raise ValueError("Pairing offer TTL must be between 30 and 300 seconds.")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 10:
            raise ValueError("Pairing attempts must be between 1 and 10.")
        if type(iterations) is not int or not 100_000 <= iterations <= 1_000_000:
            raise ValueError("Pairing KDF iterations must be between 100000 and 1000000.")
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        self.iterations = iterations
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._offer: dict[str, object] | None = None
        self._clients: dict[str, PairedLaptopClient] = {}
        self._replays: dict[str, dict[str, float]] = {}
        self._lock = threading.RLock()
        self.storage_path = Path(storage_path).expanduser() if storage_path is not None else None
        if self.storage_path is not None:
            self._initialize_storage()

    def _connect_storage(self) -> sqlite3.Connection:
        if self.storage_path is None:
            raise RuntimeError("Persistent pairing storage is not configured.")
        db = sqlite3.connect(self.storage_path, timeout=5.0)
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def _initialize_storage(self) -> None:
        path = self.storage_path
        if path is None:
            return
        if path.is_symlink():
            raise PermissionError("Laptop pairing database must not be a symbolic link.")
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        secure_owner_only(path.parent, directory=True)
        with closing(self._connect_storage()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS paired_clients (
                    client_id TEXT PRIMARY KEY,
                    session_key BLOB NOT NULL,
                    paired_at_epoch INTEGER NOT NULL,
                    permissions_json TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS replay_nonces (
                    client_id TEXT NOT NULL REFERENCES paired_clients(client_id) ON DELETE CASCADE,
                    nonce TEXT NOT NULL,
                    seen_at_epoch INTEGER NOT NULL,
                    PRIMARY KEY(client_id, nonce)
                )
            """)
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_replay_seen_at ON replay_nonces(seen_at_epoch)"
            )
        secure_owner_only(path)
        with closing(self._connect_storage()) as db, db:
            rows = db.execute(
                "SELECT client_id, session_key, paired_at_epoch, permissions_json FROM paired_clients"
            ).fetchall()
        for client_id, session_key, paired_at_epoch, permissions_json in rows:
            if (
                not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id)
                or not isinstance(session_key, bytes) or len(session_key) != 32
                or type(paired_at_epoch) is not int
            ):
                raise RuntimeError("Laptop pairing database contains an invalid client record.")
            try:
                permissions = self._permissions(json.loads(permissions_json))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError("Laptop pairing database contains invalid permissions.") from exc
            self._clients[client_id] = PairedLaptopClient(
                client_id, session_key, paired_at_epoch, permissions
            )
            self._replays[client_id] = {}

    def _get_client_locked(self, client_id: str) -> PairedLaptopClient | None:
        """Refresh persisted client state so laptop-owner revocation takes effect live."""
        if self.storage_path is None:
            return self._clients.get(client_id)
        try:
            with closing(self._connect_storage()) as db:
                row = db.execute(
                    "SELECT session_key, paired_at_epoch, permissions_json "
                    "FROM paired_clients WHERE client_id=?",
                    (client_id,),
                ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            self._clients.pop(client_id, None)
            self._replays.pop(client_id, None)
            return None
        try:
            session_key = row[0]
            paired_at_epoch = row[1]
            permissions = self._permissions(json.loads(row[2]))
            if not isinstance(session_key, bytes) or len(session_key) != 32 or type(paired_at_epoch) is not int:
                return None
            record = PairedLaptopClient(client_id, session_key, paired_at_epoch, permissions)
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
        self._clients[client_id] = record
        self._replays.setdefault(client_id, {})
        return record

    def _persist_client(self, record: PairedLaptopClient) -> None:
        if self.storage_path is None:
            return
        with closing(self._connect_storage()) as db, db:
            db.execute(
                "INSERT INTO paired_clients(client_id, session_key, paired_at_epoch, permissions_json) "
                "VALUES (?, ?, ?, ?)",
                (
                    record.client_id, sqlite3.Binary(record.session_key),
                    record.paired_at_epoch,
                    json.dumps(record.permissions, separators=(",", ":")),
                ),
            )

    @staticmethod
    def _permissions(values) -> tuple[str, ...]:
        if not isinstance(values, (list, tuple, set, frozenset)):
            raise ValueError("Laptop pairing permissions must be a collection.")
        if not values or len(values) > len(_ALLOWED_PERMISSIONS):
            raise ValueError("Laptop pairing must grant at least one known permission.")
        if any(not isinstance(value, str) or value not in _ALLOWED_PERMISSIONS for value in values):
            raise ValueError("Laptop pairing contains an unknown permission.")
        return tuple(sorted(set(values)))

    def begin_pairing(
        self,
        permissions: tuple[str, ...] = _DEFAULT_PERMISSIONS,
    ) -> PairingOffer:
        """Create a one-time code bound to a locally selected capability scope."""
        selected_permissions = self._permissions(permissions)
        with self._lock:
            code = f"{secrets.randbelow(10**12):012d}"
            salt = secrets.token_bytes(16)
            server_nonce = secrets.token_bytes(32)
            self._offer = {
                "code": code,
                "salt": salt,
                "server_nonce": server_nonce,
                "expires_at": self._monotonic() + self.ttl_seconds,
                "attempts": 0,
                "permissions": selected_permissions,
            }
            return PairingOffer(
                pairing_code=code,
                salt_b64=_b64encode(salt),
                server_nonce_b64=_b64encode(server_nonce),
                expires_in_seconds=self.ttl_seconds,
                iterations=self.iterations,
                permissions=selected_permissions,
            )

    def public_offer(self) -> dict[str, object] | None:
        """Return challenge metadata without disclosing the locally displayed pairing code."""
        with self._lock:
            offer = self._offer
            if offer is None:
                return None
            if self._monotonic() >= offer["expires_at"]:
                self._offer = None
                return None
            return {
                "salt_b64": _b64encode(offer["salt"]),
                "server_nonce_b64": _b64encode(offer["server_nonce"]),
                "expires_in_seconds": max(0, int(offer["expires_at"] - self._monotonic())),
                "iterations": self.iterations,
                "permissions": list(offer["permissions"]),
            }

    @staticmethod
    def make_client_proof(
        pairing_code: str,
        salt_b64: str,
        server_nonce_b64: str,
        client_id: str,
        client_nonce_b64: str,
        *,
        iterations: int = 310_000,
        permissions: tuple[str, ...] = _DEFAULT_PERMISSIONS,
    ) -> tuple[str, str]:
        """Return (client proof, derived session key) for the phone-side pairing flow."""
        if not isinstance(pairing_code, str) or not re.fullmatch(r"\d{12}", pairing_code):
            raise ValueError("Pairing code must contain exactly 12 digits.")
        if not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id):
            raise ValueError("Invalid laptop client identifier.")
        if type(iterations) is not int or not 100_000 <= iterations <= 1_000_000:
            raise ValueError("Invalid pairing KDF work factor.")
        selected_permissions = LaptopPairingAuthority._permissions(permissions)
        salt = _b64decode(salt_b64, expected_bytes=16)
        server_nonce = _b64decode(server_nonce_b64, expected_bytes=32)
        client_nonce = _b64decode(client_nonce_b64, expected_bytes=32)
        scope = json.dumps(selected_permissions, separators=(",", ":")).encode("ascii")
        transcript = (
            b"zexa-laptop-pair-v1\0" + server_nonce + client_nonce
            + client_id.encode("ascii") + b"\0" + scope
        )
        derived = hashlib.pbkdf2_hmac(
            "sha256", pairing_code.encode("ascii"), salt, iterations, dklen=32
        )
        proof = hmac.new(derived, b"client\0" + transcript, hashlib.sha256).digest()
        session_key = hmac.new(derived, b"session\0" + transcript, hashlib.sha256).digest()
        return _b64encode(proof), _b64encode(session_key)

    def complete_pairing(
        self,
        client_id: str,
        client_nonce_b64: str,
        client_proof_b64: str,
    ) -> PairedLaptopClient:
        if not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id):
            raise ValueError("Invalid laptop client identifier.")
        client_nonce = _b64decode(client_nonce_b64, expected_bytes=32)
        supplied_proof = _b64decode(client_proof_b64, expected_bytes=32)
        with self._lock:
            offer = self._offer
            if offer is None:
                raise PermissionError("No laptop pairing offer is active.")
            if self._monotonic() >= offer["expires_at"]:
                self._offer = None
                raise TimeoutError("Laptop pairing offer has expired.")
            if client_id in self._clients:
                raise PermissionError("This client is already paired.")
            code = offer["code"]
            salt = offer["salt"]
            server_nonce = offer["server_nonce"]
            selected_permissions = tuple(offer["permissions"])
            scope = json.dumps(selected_permissions, separators=(",", ":")).encode("ascii")
            transcript = (
                b"zexa-laptop-pair-v1\0" + server_nonce + client_nonce
                + client_id.encode("ascii") + b"\0" + scope
            )
            derived = hashlib.pbkdf2_hmac(
                "sha256", code.encode("ascii"), salt, self.iterations, dklen=32
            )
            expected = hmac.new(derived, b"client\0" + transcript, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, supplied_proof):
                offer["attempts"] = int(offer["attempts"]) + 1
                if offer["attempts"] >= self.max_attempts:
                    self._offer = None
                raise PermissionError("Laptop pairing proof was rejected.")
            session_key = hmac.new(
                derived, b"session\0" + transcript, hashlib.sha256
            ).digest()
            record = PairedLaptopClient(
                client_id=client_id,
                session_key=session_key,
                paired_at_epoch=int(self._wall_clock()),
                permissions=selected_permissions,
            )
            self._persist_client(record)
            self._clients[client_id] = record
            self._replays[client_id] = {}
            self._offer = None
            return record

    @staticmethod
    def sign_request(
        session_key_b64: str,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        timestamp: int | None = None,
        nonce_b64: str | None = None,
    ) -> dict[str, str]:
        key = _b64decode(session_key_b64, expected_bytes=32)
        timestamp = int(time.time()) if timestamp is None else timestamp
        nonce_b64 = _b64encode(secrets.token_bytes(24)) if nonce_b64 is None else nonce_b64
        LaptopPairingAuthority._validate_request_fields(method, path, body, timestamp)
        nonce = _b64decode(nonce_b64, expected_bytes=24)
        message = LaptopPairingAuthority._request_message(method, path, body, timestamp, nonce)
        mac = hmac.new(key, message, hashlib.sha256).digest()
        return {"X-Zexa-Timestamp": str(timestamp), "X-Zexa-Nonce": nonce_b64, "X-Zexa-MAC": _b64encode(mac)}

    def verify_request(
        self,
        client_id: str,
        method: str,
        path: str,
        body: bytes,
        headers: dict[str, str],
    ) -> bool:
        if not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id):
            return False
        if not isinstance(headers, dict):
            return False
        try:
            timestamp_text = headers["X-Zexa-Timestamp"]
            timestamp = int(timestamp_text)
            nonce_b64 = headers["X-Zexa-Nonce"]
            supplied_mac = _b64decode(headers["X-Zexa-MAC"], expected_bytes=32)
            self._validate_request_fields(method, path, body, timestamp)
            nonce = _b64decode(nonce_b64, expected_bytes=24)
        except (KeyError, TypeError, ValueError):
            return False
        now = int(self._wall_clock())
        if abs(now - timestamp) > 30:
            return False
        with self._lock:
            record = self._get_client_locked(client_id)
            if record is None:
                return False
            message = self._request_message(method, path, body, timestamp, nonce)
            expected = hmac.new(record.session_key, message, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, supplied_mac):
                return False
            canonical_nonce = _b64encode(nonce)
            if self.storage_path is not None:
                try:
                    with closing(self._connect_storage()) as db, db:
                        db.execute(
                            "DELETE FROM replay_nonces WHERE seen_at_epoch < ?",
                            (now - 60,),
                        )
                        count = db.execute(
                            "SELECT COUNT(*) FROM replay_nonces WHERE client_id=?",
                            (client_id,),
                        ).fetchone()[0]
                        if count >= _MAX_REPLAY_ENTRIES:
                            return False
                        db.execute(
                            "INSERT INTO replay_nonces(client_id, nonce, seen_at_epoch) VALUES (?, ?, ?)",
                            (client_id, canonical_nonce, now),
                        )
                    return True
                except sqlite3.IntegrityError:
                    return False
                except sqlite3.Error:
                    return False
            replay = self._replays.setdefault(client_id, {})
            current = self._monotonic()
            expired = [item for item, seen_at in replay.items() if current - seen_at > 60]
            for item in expired:
                replay.pop(item, None)
            if canonical_nonce in replay or len(replay) >= _MAX_REPLAY_ENTRIES:
                return False
            replay[canonical_nonce] = current
            return True

    def verify_scoped_request(
        self,
        client_id: str,
        permission: str,
        method: str,
        path: str,
        body: bytes,
        headers: dict[str, str],
    ) -> bool:
        """Authenticate a request and enforce the capability scope selected at pairing."""
        with self._lock:
            record = self._get_client_locked(client_id)
            if record is None or not record.allows(permission):
                return False
            return self.verify_request(client_id, method, path, body, headers)

    @staticmethod
    def _validate_request_fields(method: str, path: str, body: bytes, timestamp: int) -> None:
        if (
            not isinstance(method, str) or not re.fullmatch(r"[A-Z]{3,10}", method)
            or not isinstance(path, str) or not path.startswith("/")
            or len(path) > _MAX_PATH_CHARS or any(char in path for char in "\r\n\0")
            or not isinstance(body, bytes) or len(body) > _MAX_BODY_BYTES
            or type(timestamp) is not int or timestamp < 0
        ):
            raise ValueError("Invalid laptop request fields.")

    @staticmethod
    def _request_message(method: str, path: str, body: bytes, timestamp: int, nonce: bytes) -> bytes:
        body_hash = hashlib.sha256(body).hexdigest()
        return (
            b"zexa-laptop-request-v1\0"
            + method.encode("ascii") + b"\n"
            + path.encode("utf-8") + b"\n"
            + str(timestamp).encode("ascii") + b"\n"
            + nonce + b"\n"
            + body_hash.encode("ascii")
        )

    def revoke_client(self, client_id: str) -> bool:
        with self._lock:
            if self.storage_path is not None:
                try:
                    with closing(self._connect_storage()) as db, db:
                        cursor = db.execute(
                            "DELETE FROM paired_clients WHERE client_id=?", (client_id,)
                        )
                    removed = cursor.rowcount > 0
                except sqlite3.Error:
                    return False
                self._replays.pop(client_id, None)
                self._clients.pop(client_id, None)
                return removed
            self._replays.pop(client_id, None)
            return self._clients.pop(client_id, None) is not None

    def revoke_all_clients(self) -> int:
        """Revoke every paired phone and its persisted replay state."""
        with self._lock:
            if self.storage_path is not None:
                try:
                    with closing(self._connect_storage()) as db, db:
                        count = db.execute("SELECT COUNT(*) FROM paired_clients").fetchone()[0]
                        db.execute("DELETE FROM paired_clients")
                except sqlite3.Error:
                    return 0
                self._clients.clear()
                self._replays.clear()
                return int(count)
            count = len(self._clients)
            self._clients.clear()
            self._replays.clear()
            return count

    def list_clients(self) -> list[dict[str, int | str]]:
        with self._lock:
            if self.storage_path is not None:
                try:
                    with closing(self._connect_storage()) as db:
                        rows = db.execute(
                            "SELECT client_id, paired_at_epoch, permissions_json "
                            "FROM paired_clients ORDER BY client_id"
                        ).fetchall()
                except sqlite3.Error:
                    return []
                result = []
                for client_id, paired_at_epoch, permissions_json in rows:
                    try:
                        permissions = self._permissions(json.loads(permissions_json))
                        if (
                            not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id)
                            or type(paired_at_epoch) is not int
                        ):
                            continue
                    except (ValueError, TypeError, json.JSONDecodeError):
                        continue
                    result.append({
                        "client_id": client_id,
                        "paired_at_epoch": paired_at_epoch,
                        "permissions": list(permissions),
                    })
                return result
            return [
                {
                    "client_id": item.client_id,
                    "paired_at_epoch": item.paired_at_epoch,
                    "permissions": list(item.permissions),
                }
                for item in sorted(self._clients.values(), key=lambda value: value.client_id)
            ]
