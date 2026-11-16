"""Pinned-TLS phone client for the scope-limited laptop Human Hand server."""
from __future__ import annotations

import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import ssl
import stat
import tempfile
from urllib.parse import urlencode

from .laptop_hand import MAX_WRITE_CHARS
from .laptop_pairing import (
    LaptopPairingAuthority,
    _b64decode,
    _b64encode,
    secure_owner_only,
    verify_tls_fingerprint,
)


_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_CLIENT_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_ALLOWED_PERMISSIONS = {
    "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write",
}


class PairingCredentialStore:
    """Private, atomic local storage for phone-side paired laptop session keys."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zexa" / "laptop_pairings.json").expanduser()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        if self.path.is_symlink() or not self.path.is_file() or self.path.stat().st_size > 64_000:
            raise PermissionError("Laptop pairing credential file is not a safe regular file.")
        if os.name != "nt" and stat.S_IMODE(self.path.stat().st_mode) & 0o077:
            raise PermissionError("Laptop pairing credential file permissions are too broad; restrict it to the current user.")
        if os.name == "nt":
            secure_owner_only(self.path)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Laptop pairing credential file is invalid.") from exc
        if not isinstance(data, dict) or set(data) != {"version", "pairs"} or data["version"] != 1:
            raise ValueError("Unsupported laptop pairing credential file.")
        if not isinstance(data["pairs"], list) or len(data["pairs"]) > 20:
            raise ValueError("Laptop pairing credential list is invalid.")
        result = {}
        for item in data["pairs"]:
            if not isinstance(item, dict) or set(item) != {
                "host", "port", "fingerprint", "client_id", "session_key_b64", "permissions"
            }:
                raise ValueError("Laptop pairing credential entry is malformed.")
            if (
                not isinstance(item["host"], str) or not item["host"]
                or type(item["port"]) is not int or not 1024 <= item["port"] <= 65535
                or not isinstance(item["fingerprint"], str)
                or not _FINGERPRINT.fullmatch(item["fingerprint"])
                or not isinstance(item["client_id"], str)
                or not _CLIENT_ID.fullmatch(item["client_id"])
                or not isinstance(item["permissions"], list)
                or not item["permissions"]
                or any(permission not in _ALLOWED_PERMISSIONS for permission in item["permissions"])
            ):
                raise ValueError("Laptop pairing credential fields are invalid.")
            _b64decode(item["session_key_b64"], expected_bytes=32)
            key = self._key(item["host"], item["port"], item["client_id"])
            result[key] = item
        return result

    @staticmethod
    def _key(host: str, port: int, client_id: str) -> str:
        return f"{host}:{port}:{client_id}"

    def save(
        self,
        host: str,
        port: int,
        fingerprint: str,
        client_id: str,
        session_key_b64: str,
        permissions: tuple[str, ...],
    ) -> None:
        normalized = fingerprint.replace(":", "").strip().lower()
        if (
            not isinstance(host, str) or not host
            or type(port) is not int or not 1024 <= port <= 65535
            or not _FINGERPRINT.fullmatch(normalized)
            or not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id)
            or not isinstance(permissions, (tuple, list))
            or not permissions or any(item not in _ALLOWED_PERMISSIONS for item in permissions)
        ):
            raise ValueError("Invalid laptop pairing credential.")
        _b64decode(session_key_b64, expected_bytes=32)
        pairs = self._load()
        item = {
            "host": host,
            "port": port,
            "fingerprint": normalized,
            "client_id": client_id,
            "session_key_b64": session_key_b64,
            "permissions": sorted(set(permissions)),
        }
        pairs[self._key(host, port, client_id)] = item
        if len(pairs) > 20:
            raise ValueError("At most 20 laptop pairings can be stored.")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        secure_owner_only(self.path.parent, directory=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".laptop-pairings-", dir=self.path.parent)
        try:
            try:
                os.fchmod(descriptor, 0o600)
            except (AttributeError, OSError):
                pass
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                json.dump({"version": 1, "pairs": list(pairs.values())}, target, ensure_ascii=False)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.path)
            secure_owner_only(self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    def get(self, host: str, port: int, client_id: str) -> dict | None:
        return self._load().get(self._key(host, port, client_id))

    def delete(self, host: str, port: int, client_id: str) -> bool:
        pairs = self._load()
        key = self._key(host, port, client_id)
        if key not in pairs:
            return False
        pairs.pop(key)
        if not pairs:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        secure_owner_only(self.path.parent, directory=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".laptop-pairings-", dir=self.path.parent)
        try:
            try:
                os.fchmod(descriptor, 0o600)
            except OSError:
                pass
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                json.dump({"version": 1, "pairs": list(pairs.values())}, target, ensure_ascii=False)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.path)
            secure_owner_only(self.path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        return True


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, port: int, fingerprint: str, timeout: float = 8.0):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        self._expected_fingerprint = fingerprint
        super().__init__(host, port, timeout=timeout, context=context)

    def connect(self):
        super().connect()
        certificate = self.sock.getpeercert(binary_form=True)
        if not verify_tls_fingerprint(certificate, self._expected_fingerprint):
            self.close()
            raise ssl.SSLError("Laptop TLS certificate fingerprint does not match the locally confirmed pin.")


class LaptopAgentClient:
    """Phone-side pinned-TLS client for one explicitly paired laptop."""

    def __init__(
        self,
        host: str,
        port: int,
        fingerprint: str | None,
        client_id: str,
        store: PairingCredentialStore | None = None,
        timeout: float = 8.0,
    ) -> None:
        if not isinstance(host, str) or not host:
            raise ValueError("Laptop host is required.")
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("Laptop host must be a literal private IPv4 address.") from exc
        allowed_networks = (
            ipaddress.ip_network("10.0.0.0/8"),
            ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"),
        )
        if address.version != 4 or not (
            address.is_loopback or any(address in network for network in allowed_networks)
        ):
            raise ValueError("Laptop connection may target only loopback or a private IPv4 address.")
        host = str(address)
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Laptop port must be between 1024 and 65535.")
        if not isinstance(client_id, str) or not _CLIENT_ID.fullmatch(client_id):
            raise ValueError("Invalid laptop client identifier.")
        self.store = store or PairingCredentialStore()
        if fingerprint is None:
            saved = self.store.get(host, port, client_id)
            if saved is None:
                raise PermissionError("No saved laptop pairing or TLS fingerprint exists for this client.")
            normalized = saved["fingerprint"]
        else:
            normalized = fingerprint.replace(":", "").strip().lower() if isinstance(fingerprint, str) else ""
            if not _FINGERPRINT.fullmatch(normalized):
                raise ValueError("A confirmed 64-character SHA-256 TLS fingerprint is required.")
        self.host = host
        self.port = port
        self.fingerprint = normalized
        self.client_id = client_id
        self.timeout = max(2.0, min(float(timeout), 20.0))

    def _request(self, method: str, path: str, body: bytes = b"", headers: dict[str, str] | None = None):
        connection = _PinnedHTTPSConnection(
            self.host, self.port, self.fingerprint, timeout=self.timeout
        )
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            if response.getheader("Content-Type", "").split(";", 1)[0].lower() != "application/json":
                raise RuntimeError("Laptop agent returned a non-JSON response.")
            raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise RuntimeError("Laptop agent response exceeded the size limit.")
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("Laptop agent returned invalid JSON.") from exc
            if not isinstance(payload, dict):
                raise RuntimeError("Laptop agent returned an invalid response object.")
            return response.status, payload
        finally:
            connection.close()

    def pair(self, pairing_code: str) -> dict:
        status, response = self._request("GET", "/v1/pair/offer")
        if status != 200 or response.get("ok") is not True or not isinstance(response.get("offer"), dict):
            raise PermissionError("Laptop does not have an active pairing offer.")
        offer = response["offer"]
        if set(offer) != {"salt_b64", "server_nonce_b64", "expires_in_seconds", "iterations", "permissions"}:
            raise RuntimeError("Laptop pairing offer has an unexpected schema.")
        if (
            type(offer["expires_in_seconds"]) is not int or offer["expires_in_seconds"] <= 0
            or type(offer["iterations"]) is not int
            or not isinstance(offer["permissions"], list)
            or not offer["permissions"]
            or any(item not in _ALLOWED_PERMISSIONS for item in offer["permissions"])
        ):
            raise RuntimeError("Laptop pairing offer is invalid.")
        client_nonce = _b64encode(secrets.token_bytes(32))
        proof, session_key = LaptopPairingAuthority.make_client_proof(
            pairing_code,
            offer["salt_b64"],
            offer["server_nonce_b64"],
            self.client_id,
            client_nonce,
            iterations=offer["iterations"],
            permissions=tuple(offer["permissions"]),
        )
        body = json.dumps({
            "client_id": self.client_id,
            "client_nonce_b64": client_nonce,
            "client_proof_b64": proof,
        }, separators=(",", ":")).encode("utf-8")
        status, result = self._request(
            "POST", "/v1/pair/complete", body,
            {"Content-Type": "application/json", "Content-Length": str(len(body))},
        )
        if status != 200 or result.get("ok") is not True:
            raise PermissionError("Laptop pairing was rejected.")
        if (
            result.get("client_id") != self.client_id
            or result.get("permissions") != offer["permissions"]
        ):
            raise RuntimeError("Laptop pairing response does not match the requested scope.")
        self.store.save(
            self.host, self.port, self.fingerprint, self.client_id,
            session_key, tuple(offer["permissions"]),
        )
        return {"client_id": self.client_id, "permissions": offer["permissions"]}

    def _signed_headers(self, method: str, path: str, body: bytes = b"") -> dict[str, str]:
        record = self.store.get(self.host, self.port, self.client_id)
        if record is None:
            raise PermissionError("This phone is not paired with the selected laptop.")
        headers = LaptopPairingAuthority.sign_request(
            record["session_key_b64"], method, path, body
        )
        headers["X-Zexa-Client-ID"] = self.client_id
        return headers

    def list_directory(self, relative_dir: str = ".") -> dict:
        path = "/v1/workspace/list?" + urlencode({"dir": relative_dir})
        headers = self._signed_headers("GET", path)
        status, response = self._request("GET", path, headers=headers)
        if status != 200 or response.get("ok") is not True:
            raise PermissionError("Laptop workspace listing was denied or failed.")
        return response["result"]

    def read_text(self, relative_path: str) -> dict:
        path = "/v1/workspace/read?" + urlencode({"path": relative_path})
        headers = self._signed_headers("GET", path)
        status, response = self._request("GET", path, headers=headers)
        if status != 200 or response.get("ok") is not True:
            raise PermissionError("Laptop workspace read was denied or failed.")
        return response["result"]

    def write_text(
        self,
        relative_path: str,
        content: str,
        *,
        overwrite: bool = False,
        user_confirmed: bool = False,
    ) -> dict:
        """Write one workspace text file after an explicit caller confirmation."""
        if user_confirmed is not True:
            raise PermissionError("A fresh explicit user confirmation is required for remote writes.")
        record = self.store.get(self.host, self.port, self.client_id)
        if record is None or "laptop.workspace.write" not in record["permissions"]:
            raise PermissionError("This phone was not paired with remote workspace write permission.")
        if (
            not isinstance(content, str) or not content.strip()
            or len(content) > MAX_WRITE_CHARS
            or any((ord(char) < 32 and char not in "\\r\\n\\t") or ord(char) == 127 for char in content)
        ):
            raise ValueError("Remote workspace content must contain 1–128000 characters without unsupported control codes.")
        if type(overwrite) is not bool:
            raise ValueError("overwrite must be a boolean.")
        path = "/v1/workspace/write"
        body = json.dumps({
            "relative_path": relative_path,
            "content": content,
            "overwrite": overwrite,
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = LaptopPairingAuthority.sign_request(
            record["session_key_b64"], "POST", path, body
        )
        headers.update({
            "X-Zexa-Client-ID": self.client_id,
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        status, response = self._request("POST", path, body, headers)
        if status == 409:
            raise FileExistsError("Laptop workspace file already exists.")
        if status in {401, 403}:
            raise PermissionError("Laptop rejected the workspace write or its approval scope.")
        if status != 200 or response.get("ok") is not True:
            raise RuntimeError("Laptop workspace write failed.")
        return response["result"]

    def revoke_pairing(self) -> bool:
        """Revoke this phone's server-side key, then remove its local credential."""
        headers = self._signed_headers("POST", "/v1/pair/revoke")
        status, response = self._request(
            "POST", "/v1/pair/revoke", headers=headers
        )
        if status == 200 and response.get("revoked") is True:
            self.store.delete(self.host, self.port, self.client_id)
            return True
        if status == 404:
            self.store.delete(self.host, self.port, self.client_id)
            return False
        raise PermissionError("Laptop pairing revocation was denied or failed.")

    def forget_local_pairing(self) -> bool:
        return self.store.delete(self.host, self.port, self.client_id)
