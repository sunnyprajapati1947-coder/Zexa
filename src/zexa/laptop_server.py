"""TLS-only, scope-limited laptop Human Hand HTTP server.

The server exposes pairing, workspace list/read, and optional explicitly scoped
text writes. It never exposes a shell, process execution, app launch, or
arbitrary URL fetch.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import shutil
import subprocess
import tempfile
import stat
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import ssl
from urllib.parse import parse_qs, urlsplit

from .audit import AuditLog
from .laptop_hand import MAX_WRITE_CHARS, LaptopWorkspace
from .laptop_pairing import LaptopPairingAuthority


MAX_PAIR_BODY = 16_384
MAX_WRITE_BODY = MAX_WRITE_CHARS * 4 + 4096


def certificate_fingerprint(cert_file: str | Path) -> str:
    """Return the SHA-256 fingerprint of a PEM certificate for local display."""
    path = Path(cert_file).expanduser()
    pem = path.read_text(encoding="ascii")
    der = ssl.PEM_cert_to_DER_cert(pem)
    return hashlib.sha256(der).hexdigest()


def generate_laptop_certificate(
    host: str,
    certificate_file: str | Path,
    private_key_file: str | Path,
) -> str:
    """Generate a self-signed TLS certificate pinned by fingerprint on the phone."""
    host = _private_ipv4(host)
    cert = Path(certificate_file).expanduser()
    key = Path(private_key_file).expanduser()
    if cert.resolve() == key.resolve() or cert.parent.resolve() != key.parent.resolve():
        raise ValueError("TLS certificate and private key must be different files in the same directory.")
    if cert.exists() or key.exists():
        raise FileExistsError("TLS certificate or private key already exists; refusing to overwrite.")
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("OpenSSL is required to generate the laptop TLS certificate.")
    cert.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(cert.parent, 0o700)
    except OSError:
        pass
    with tempfile.TemporaryDirectory(prefix=".zexa-tls-", dir=cert.parent) as temp_dir:
        temp_cert = Path(temp_dir) / "laptop.crt"
        temp_key = Path(temp_dir) / "laptop.key"
        command = [
            openssl, "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes",
            "-keyout", str(temp_key), "-out", str(temp_cert), "-days", "365",
            "-subj", "/CN=Zexa-Laptop-Hand",
            "-addext", f"subjectAltName=IP:{host}",
        ]
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=45,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "OpenSSL certificate generation failed.")[-500:]
            raise RuntimeError(detail) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("OpenSSL certificate generation timed out.") from exc
        os.chmod(temp_key, 0o600)
        os.replace(temp_key, key)
        os.replace(temp_cert, cert)
    return certificate_fingerprint(cert)


def _private_ipv4(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("Laptop agent must bind to a literal private IPv4 address.") from exc
    allowed_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )
    if address.version != 4 or not (
        address.is_loopback or any(address in network for network in allowed_networks)
    ):
        raise ValueError("Laptop agent may bind only to loopback or a private IPv4 address.")
    return str(address)


class _LaptopHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, workspace, authority, audit):
        self.workspace = workspace
        self.authority = authority
        self.audit = audit
        self._worker_slots = threading.BoundedSemaphore(8)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._worker_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Connection: close\r\nContent-Length: 0\r\n\r\n"
                )
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()


def make_laptop_handler():
    class Handler(BaseHTTPRequestHandler):
        server_version = "ZexaLaptopHand"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(5.0)

        def log_message(self, _format, *_args):
            # Do not log file paths, request headers, authentication metadata, or content.
            return

        def _send(self, status: int, payload: object) -> None:
            raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self, limit: int = MAX_PAIR_BODY) -> dict:
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Transfer-Encoding is not supported.")
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise ValueError("application/json is required.")
            raw_length = self.headers.get("Content-Length", "")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("A valid Content-Length is required.") from exc
            if not 1 <= length <= limit:
                raise ValueError("Request body is empty or too large.")
            raw = self.rfile.read(length)
            self._last_body = raw
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            return payload

        def _audit(self, event_type: str, actor: str, action: str, decision: str, details=None):
            self.server.audit.record(
                event_type, actor=actor or "unknown", action=action,
                decision=decision, details=details or {},
            )

        def _authorized(self, permission: str, body: bytes = b"") -> bool:
            client_id = self.headers.get("X-Zexa-Client-ID", "")
            signed_headers = {
                "X-Zexa-Timestamp": self.headers.get("X-Zexa-Timestamp", ""),
                "X-Zexa-Nonce": self.headers.get("X-Zexa-Nonce", ""),
                "X-Zexa-MAC": self.headers.get("X-Zexa-MAC", ""),
            }
            if not self.server.authority.verify_scoped_request(
                client_id, permission, self.command, self.path, body, signed_headers
            ):
                self._send(401, {"error": "unauthorized_or_scope_denied"})
                return False
            return True

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/v1/pair/offer" and not parsed.query:
                offer = self.server.authority.public_offer()
                if offer is None:
                    return self._send(404, {"error": "no_active_pairing_offer"})
                return self._send(200, {"ok": True, "offer": offer})

            if parsed.path == "/v1/workspace/list":
                try:
                    query = parse_qs(parsed.query, strict_parsing=True, keep_blank_values=True)
                    if set(query) - {"dir"} or any(len(values) != 1 for values in query.values()):
                        raise ValueError("Invalid directory query.")
                    relative_dir = query.get("dir", ["."])[0] or "."
                    if not self._authorized("laptop.workspace.list"):
                        return
                    result = self.server.workspace.list_directory(relative_dir)
                    self._audit(
                        "laptop_workspace_list",
                        self.headers.get("X-Zexa-Client-ID", ""),
                        "workspace.list", "allowed",
                        {"relative_dir": relative_dir, "entry_count": len(result["entries"])},
                    )
                    return self._send(200, {"ok": True, "result": result})
                except PermissionError:
                    return self._send(403, {"error": "workspace_scope_denied"})
                except (ValueError, OSError) as exc:
                    return self._send(400, {"error": str(exc)[:200]})

            if parsed.path == "/v1/workspace/read":
                try:
                    query = parse_qs(parsed.query, strict_parsing=True, keep_blank_values=True)
                    if set(query) != {"path"} or len(query["path"]) != 1:
                        raise ValueError("Exactly one path query is required.")
                    if not self._authorized("laptop.workspace.read"):
                        return
                    result = self.server.workspace.read_text(query["path"][0])
                    self._audit(
                        "laptop_workspace_read",
                        self.headers.get("X-Zexa-Client-ID", ""),
                        "workspace.read", "allowed",
                        {
                            "relative_path": result["relative_path"],
                            "size_bytes": result["size_bytes"],
                            "sha256": result["sha256"],
                            "redacted": result["redacted"],
                        },
                    )
                    return self._send(200, {"ok": True, "result": result})
                except PermissionError:
                    return self._send(403, {"error": "workspace_scope_denied"})
                except (ValueError, OSError) as exc:
                    return self._send(400, {"error": str(exc)[:200]})

            return self._send(404, {"error": "not_found"})

        def do_POST(self):
            if self.path == "/v1/workspace/write":
                try:
                    payload = self._read_json(limit=MAX_WRITE_BODY)
                    if set(payload) != {"relative_path", "content", "overwrite"}:
                        raise ValueError("Invalid workspace write fields.")
                    if not self._authorized("laptop.workspace.write", self._last_body):
                        return
                    self._audit(
                        "laptop_workspace_write",
                        self.headers.get("X-Zexa-Client-ID", ""),
                        "workspace.write", "requested",
                        {
                            "relative_path": payload["relative_path"],
                            "size_chars": len(payload["content"]) if isinstance(payload["content"], str) else 0,
                            "overwrite": payload["overwrite"],
                        },
                    )
                    result = self.server.workspace.write_text(
                        payload["relative_path"], payload["content"], payload["overwrite"]
                    )
                    self._audit(
                        "laptop_workspace_write",
                        self.headers.get("X-Zexa-Client-ID", ""),
                        "workspace.write", "completed",
                        {
                            "relative_path": result["relative_path"],
                            "size_bytes": result["size_bytes"],
                            "sha256": result["sha256"],
                            "overwrite": payload["overwrite"],
                        },
                    )
                    return self._send(200, {"ok": True, "result": result})
                except PermissionError:
                    return self._send(403, {"error": "workspace_scope_denied"})
                except FileExistsError:
                    return self._send(409, {"error": "workspace_file_exists"})
                except (ValueError, OSError, TypeError) as exc:
                    return self._send(400, {"error": str(exc)[:200]})
            if self.path == "/v1/pair/revoke":
                client_id = self.headers.get("X-Zexa-Client-ID", "")
                if not self._authorized("laptop.workspace.list"):
                    return
                if self.server.authority.revoke_client(client_id):
                    self._audit(
                        "laptop_pairing_revoke", client_id, "pairing.revoke", "revoked", {}
                    )
                    return self._send(200, {"ok": True, "revoked": True})
                return self._send(404, {"error": "paired_client_not_found"})
            if self.path != "/v1/pair/complete":
                return self._send(404, {"error": "not_found"})
            try:
                payload = self._read_json()
                if set(payload) != {"client_id", "client_nonce_b64", "client_proof_b64"}:
                    raise ValueError("Invalid pairing request fields.")
                record = self.server.authority.complete_pairing(
                    payload["client_id"],
                    payload["client_nonce_b64"],
                    payload["client_proof_b64"],
                )
                self._audit(
                    "laptop_pairing", record.client_id, "pairing.complete", "approved",
                    {"permissions": list(record.permissions)},
                )
                return self._send(200, {
                    "ok": True,
                    "client_id": record.client_id,
                    "permissions": list(record.permissions),
                    "paired_at_epoch": record.paired_at_epoch,
                })
            except PermissionError:
                actor = payload.get("client_id", "unknown") if "payload" in locals() and isinstance(payload, dict) else "unknown"
                self._audit("laptop_pairing", actor, "pairing.complete", "denied", {})
                return self._send(403, {"error": "pairing_rejected"})
            except TimeoutError:
                return self._send(410, {"error": "pairing_offer_expired"})
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError, OSError) as exc:
                return self._send(400, {"error": str(exc)[:200]})

        def do_PUT(self):
            return self._send(404, {"error": "not_found"})

        def do_DELETE(self):
            return self._send(404, {"error": "not_found"})

    return Handler


class LaptopAgentServer:
    """Explicitly started TLS server exposing scoped workspace capabilities."""

    def __init__(
        self,
        host: str,
        port: int,
        certificate_file: str | Path,
        private_key_file: str | Path,
        workspace: LaptopWorkspace,
        authority: LaptopPairingAuthority | None = None,
        audit_path: str | Path | None = None,
        pairing_path: str | Path | None = None,
    ) -> None:
        host = _private_ipv4(host)
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Laptop agent port must be between 1024 and 65535.")
        if not isinstance(workspace, LaptopWorkspace):
            raise TypeError("A configured LaptopWorkspace is required.")
        cert = Path(certificate_file).expanduser()
        key = Path(private_key_file).expanduser()
        if (
            cert.is_symlink() or key.is_symlink()
            or not cert.is_file() or not key.is_file()
            or cert.stat().st_size > 64_000 or key.stat().st_size > 64_000
        ):
            raise FileNotFoundError("TLS certificate and private key must be bounded regular files, not symlinks.")
        if os.name != "nt" and stat.S_IMODE(key.stat().st_mode) & 0o077:
            raise PermissionError("Laptop TLS private key permissions must be owner-only (0600).")
        self.authority = authority or LaptopPairingAuthority(storage_path=pairing_path)
        audit_file = Path(audit_path or (Path.home() / ".zexa" / "laptop_audit.sqlite3")).expanduser()
        audit_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(audit_file.parent, 0o700)
        except OSError:
            pass
        self.audit = AuditLog(audit_file)
        try:
            os.chmod(audit_file, 0o600)
        except OSError:
            pass
        self.workspace = workspace
        self.host = host
        self.port = port
        self.certificate_file = cert
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(cert), str(key))
        self._server = _LaptopHTTPServer(
            (host, port), make_laptop_handler(), workspace, self.authority, self.audit
        )
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)

    def begin_pairing(self, permissions=("laptop.workspace.list", "laptop.workspace.read")):
        return self.authority.begin_pairing(permissions=permissions)

    def serve_forever(self) -> None:
        self._server.serve_forever(poll_interval=0.5)

    def close(self) -> None:
        """Close the listener after serve_forever returns."""
        self._server.server_close()

    def shutdown(self) -> None:
        """Stop serve_forever from another thread and close the listener."""
        self._server.shutdown()
        self._server.server_close()
