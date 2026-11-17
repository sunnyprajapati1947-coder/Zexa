"""Scoped laptop-side workspace adapter for Zexa Human Hand.

This module deliberately provides workspace file operations only. It does not
open a network listener, run shell commands, launch arbitrary applications, or
pair devices. Remote pairing is a separate protocol and is not yet implemented.
"""
from __future__ import annotations

import os
import hashlib
import re
import stat
from pathlib import Path, PurePosixPath
import tempfile
from typing import Any

from .capabilities import CapabilitySpec


MAX_READ_BYTES = 256_000
MAX_WRITE_CHARS = 128_000
MAX_LIST_ENTRIES = 200
_TEXT_SUFFIXES = {
    ".txt", ".md", ".rst", ".json", ".csv", ".tsv", ".py", ".js", ".ts",
    ".html", ".css", ".yaml", ".yml", ".toml", ".ini", ".xml", ".sh",
    ".kt", ".java", ".gradle", ".properties",
}
_BLOCKED_NAMES = {
    ".env", ".env.local", ".env.production", "credentials", "secrets",
    "id_rsa", "id_ed25519", "known_hosts", "authorized_keys",
}
_SECRET_ASSIGNMENT = re.compile(
    r"(?im)^(\s*(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|password|passwd|secret|authorization)\s*[:=]\s*).+$"
)
_BEARER_TOKEN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}")
_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")
_AWS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)


def redact_workspace_text(value: str) -> tuple[str, bool]:
    """Redact common credential patterns before text leaves the laptop workspace."""
    redacted = _PRIVATE_KEY_BLOCK.sub("[REDACTED PRIVATE KEY]", value)
    redacted = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", redacted)
    redacted = _BEARER_TOKEN.sub("Bearer [REDACTED]", redacted)
    redacted = _GITHUB_TOKEN.sub("[REDACTED GITHUB TOKEN]", redacted)
    redacted = _AWS_KEY.sub("[REDACTED AWS KEY]", redacted)
    redacted = _JWT.sub("[REDACTED JWT]", redacted)
    return redacted, redacted != value


class LaptopWorkspace:
    """File operations constrained to one user-selected workspace directory."""

    def __init__(self, root: str | Path) -> None:
        candidate = Path(root).expanduser()
        if not candidate.exists() or not candidate.is_dir():
            raise ValueError("Laptop workspace must be an existing directory.")
        self.root = candidate.resolve(strict=True)

    @staticmethod
    def _relative(value: str) -> PurePosixPath:
        if (
            not isinstance(value, str) or not value.strip() or len(value) > 240
            or "\x00" in value or "\\" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
        ):
            raise ValueError("Workspace paths must be non-empty relative POSIX paths.")
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
            raise ValueError("Workspace path traversal or absolute paths are not allowed.")
        return path

    def _resolve_directory(self, relative_dir: str) -> Path:
        relative = self._relative(relative_dir)
        candidate = self.root.joinpath(*relative.parts)
        resolved = candidate.resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_dir():
            raise PermissionError("Workspace directory is outside the configured root.")
        return resolved

    def _resolve_file(self, relative_path: str, *, must_exist: bool) -> Path:
        relative = self._relative(relative_path)
        candidate = self.root.joinpath(*relative.parts)
        parent = candidate.parent.resolve(strict=True)
        if not parent.is_relative_to(self.root):
            raise PermissionError("Workspace file is outside the configured root.")
        target = parent / candidate.name
        if target.is_symlink():
            raise PermissionError("Workspace symlinks are not supported.")
        if must_exist:
            resolved = target.resolve(strict=True)
            if not resolved.is_relative_to(self.root) or not resolved.is_file():
                raise PermissionError("Workspace file is outside the configured root or is not a file.")
            return resolved
        if target.exists() and not target.is_file():
            raise ValueError("Workspace target must be a regular file.")
        return target

    @staticmethod
    def _sensitive_name(path: Path) -> bool:
        name = path.name.casefold()
        return (
            name in _BLOCKED_NAMES
            or name.startswith(".env.")
            or name.endswith((".pem", ".key", ".p12", ".pfx", ".keystore", ".sqlite", ".db"))
            or any(word in name for word in ("password", "secret", "credential", "token"))
        )

    def list_directory(self, relative_dir: str = ".") -> dict[str, Any]:
        if relative_dir == ".":
            directory = self.root
        else:
            directory = self._resolve_directory(relative_dir)
        entries = []
        for item in sorted(directory.iterdir(), key=lambda entry: entry.name.casefold()):
            if len(entries) >= MAX_LIST_ENTRIES:
                break
            if item.is_symlink():
                continue
            try:
                resolved = item.resolve(strict=True)
                if not resolved.is_relative_to(self.root):
                    continue
                is_dir = resolved.is_dir()
                is_file = resolved.is_file()
                if not (is_dir or is_file):
                    continue
                entries.append({
                    "name": item.name[:240],
                    "kind": "directory" if is_dir else "file",
                    "size_bytes": resolved.stat().st_size if is_file else 0,
                    "readable_text": bool(
                        is_file and not self._sensitive_name(item)
                        and item.suffix.casefold() in _TEXT_SUFFIXES
                    ),
                })
            except OSError:
                continue
        return {"relative_dir": relative_dir, "entries": entries, "truncated": len(entries) >= MAX_LIST_ENTRIES}

    def read_text(self, relative_path: str) -> dict[str, Any]:
        path = self._resolve_file(relative_path, must_exist=True)
        if self._sensitive_name(path) or path.suffix.casefold() not in _TEXT_SUFFIXES:
            raise PermissionError("This file type or filename is excluded from workspace reading.")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise PermissionError("Only regular workspace files can be read.")
            with os.fdopen(descriptor, "rb") as source:
                raw = source.read(MAX_READ_BYTES + 1)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        if len(raw) > MAX_READ_BYTES:
            raise ValueError("Workspace text file exceeds the 256 KB read limit.")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Workspace file is not valid UTF-8 text.") from exc
        safe_text, was_redacted = redact_workspace_text(text)
        return {
            "relative_path": relative_path,
            "content": safe_text,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "redacted": was_redacted,
        }

    def write_text(self, relative_path: str, content: str, overwrite: bool = False) -> dict[str, Any]:
        path = self._resolve_file(relative_path, must_exist=False)
        if self._sensitive_name(path) or path.suffix.casefold() not in _TEXT_SUFFIXES:
            raise PermissionError("This file type or filename is excluded from workspace writing.")
        if (
            not isinstance(content, str) or not content.strip()
            or len(content) > MAX_WRITE_CHARS
            or any((ord(char) < 32 and char not in "\\r\\n\\t") or ord(char) == 127 for char in content)
        ):
            raise ValueError("Workspace content must contain 1–128000 characters without unsupported control codes.")
        if type(overwrite) is not bool:
            raise ValueError("overwrite must be a boolean.")
        if path.exists() and not overwrite:
            raise FileExistsError("Workspace file already exists; explicit overwrite approval is required.")
        raw = content.encode("utf-8")
        descriptor, temporary_name = tempfile.mkstemp(prefix=".zexa-write-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as target:
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
            if overwrite:
                # Replacing a symlink replaces the link itself; it never follows
                # the link to modify a target outside the workspace.
                os.replace(temporary_name, path)
            else:
                # Hard-link creation is atomic and fails if any directory entry
                # already occupies the destination; this closes the no-clobber race.
                os.link(temporary_name, path, follow_symlinks=False)
                os.unlink(temporary_name)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        return {
            "relative_path": relative_path,
            "written": True,
            "sha256": __import__("hashlib").sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        }


def build_laptop_capabilities(workspace: LaptopWorkspace) -> dict[str, CapabilitySpec]:
    """Return trusted, workspace-scoped capabilities for CapabilityController."""
    if not isinstance(workspace, LaptopWorkspace):
        raise TypeError("A configured LaptopWorkspace is required.")
    return {
        "laptop.workspace.list": CapabilitySpec(
            name="laptop.workspace.list",
            description="List files and folders inside the configured laptop workspace.",
            permission="laptop.workspace.read",
            risk_level="low",
            platform="laptop",
            input_schema={"relative_dir": "string"},
            output_schema={"relative_dir": "string", "entries": "array", "truncated": "boolean"},
            handler=lambda data: workspace.list_directory(data["relative_dir"]),
        ),
        "laptop.workspace.read": CapabilitySpec(
            name="laptop.workspace.read",
            description="Read a bounded UTF-8 text file inside the configured laptop workspace.",
            permission="laptop.workspace.read",
            risk_level="low",
            platform="laptop",
            input_schema={"relative_path": "string"},
            output_schema={"relative_path": "string", "content": "string", "sha256": "string", "size_bytes": "integer", "redacted": "boolean"},
            max_output_chars=MAX_READ_BYTES + 2048,
            handler=lambda data: workspace.read_text(data["relative_path"]),
        ),
        "laptop.workspace.write": CapabilitySpec(
            name="laptop.workspace.write",
            description="Write a bounded text file inside the configured laptop workspace.",
            permission="laptop.workspace.write",
            risk_level="high",
            platform="laptop",
            input_schema={"relative_path": "string", "content": "string", "overwrite": "boolean"},
            output_schema={"relative_path": "string", "written": "boolean", "sha256": "string", "size_bytes": "integer"},
            max_input_chars=MAX_WRITE_CHARS + 1024,
            handler=lambda data: workspace.write_text(
                data["relative_path"], data["content"], data["overwrite"]
            ),
        ),
    }
