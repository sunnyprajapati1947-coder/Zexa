"""Approval-gated, backed-up workspace file repair transactions.

This module never executes shell commands. Callers must supply exact replacement
text and obtain a one-time approval bound to the target path and content hashes.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from .approvals import ApprovalManager


_MAX_FILE_BYTES = 256 * 1024


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class RepairTransaction:
    """Apply and roll back one explicitly approved workspace text-file change."""

    def __init__(self, workspace: str | Path, approvals: ApprovalManager,
                 backup_dir: str = ".zexa/repair-backups") -> None:
        self.workspace = Path(workspace).resolve()
        self.approvals = approvals
        self.backup_root = (self.workspace / backup_dir).resolve()
        if not self._inside(self.backup_root):
            raise ValueError("Backup directory must remain inside the workspace.")

    def _inside(self, path: Path) -> bool:
        try:
            path.relative_to(self.workspace)
            return True
        except ValueError:
            return False

    def _target(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path or "\x00" in relative_path:
            raise ValueError("A workspace-relative file path is required.")
        candidate = self.workspace / relative_path
        if candidate.is_symlink():
            raise ValueError("Symbolic-link targets are not supported.")
        resolved = candidate.resolve()
        if not self._inside(resolved) or resolved == self.workspace:
            raise ValueError("Repair target must remain inside the workspace.")
        if not resolved.is_file():
            raise ValueError("Repair target must be an existing regular file.")
        if resolved.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("Repair target exceeds the 256 KiB limit.")
        return resolved

    def preview(self, relative_path: str, replacement: str) -> dict:
        """Return hashes and a review payload; does not write any file."""
        if not isinstance(replacement, str):
            raise ValueError("Replacement content must be text.")
        encoded = replacement.encode("utf-8")
        if len(encoded) > _MAX_FILE_BYTES:
            raise ValueError("Replacement exceeds the 256 KiB limit.")
        target = self._target(relative_path)
        original = target.read_bytes()
        try:
            original.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Only UTF-8 text files can be repaired.") from exc
        return {
            "action": "repair.replace_file",
            "path": target.relative_to(self.workspace).as_posix(),
            "original_sha256": _sha256(original),
            "replacement_sha256": _sha256(encoded),
            "replacement_bytes": len(encoded),
            "backup_required": True,
            "approval_required": True,
            "commands_executed": False,
        }

    def apply(self, relative_path: str, replacement: str, approval_token: str) -> dict:
        """Back up then atomically replace a file after exact one-time approval."""
        preview = self.preview(relative_path, replacement)
        payload = {
            "path": preview["path"],
            "original_sha256": preview["original_sha256"],
            "replacement_sha256": preview["replacement_sha256"],
        }
        if not self.approvals.consume(approval_token, "repair.replace_file", payload):
            raise PermissionError("A matching, unexpired, one-time repair approval is required.")
        target = self._target(relative_path)
        original = target.read_bytes()
        if _sha256(original) != preview["original_sha256"]:
            raise RuntimeError("Repair target changed after approval; create a new preview.")
        replacement_bytes = replacement.encode("utf-8")
        self.backup_root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.backup_root, 0o700)
        except OSError:
            pass
        backup_name = f"{preview['original_sha256']}-{preview['replacement_sha256']}.bak"
        backup = self.backup_root / backup_name
        if backup.exists():
            raise FileExistsError("A backup with this transaction identity already exists.")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(backup, flags, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            backup.unlink(missing_ok=True)
            raise
        fd, temporary = tempfile.mkstemp(prefix=".zexa-repair-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(replacement_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, target.stat().st_mode & 0o777)
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            backup.unlink(missing_ok=True)
            raise
        return {
            "status": "applied",
            "path": preview["path"],
            "backup": backup.relative_to(self.workspace).as_posix(),
            "original_sha256": preview["original_sha256"],
            "applied_sha256": preview["replacement_sha256"],
            "rollback_requires_new_approval": True,
        }

    def rollback(self, relative_path: str, backup_relative_path: str,
                 applied_sha256: str, approval_token: str) -> dict:
        """Restore a transaction backup only if the live file is still unchanged."""
        target = self._target(relative_path)
        backup = (self.workspace / backup_relative_path).resolve()
        if not self._inside(backup) or not backup.is_file() or backup.is_symlink():
            raise ValueError("Backup must be an existing regular file inside the workspace.")
        if backup.stat().st_size > _MAX_FILE_BYTES:
            raise ValueError("Backup exceeds the 256 KiB limit.")
        current = target.read_bytes()
        original = backup.read_bytes()
        try:
            original.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Backup is not valid UTF-8 text.") from exc
        if _sha256(current) != applied_sha256:
            raise RuntimeError("Target changed since repair; refusing unsafe rollback.")
        payload = {
            "path": target.relative_to(self.workspace).as_posix(),
            "current_sha256": _sha256(current),
            "restore_sha256": _sha256(original),
        }
        if not self.approvals.consume(approval_token, "repair.rollback_file", payload):
            raise PermissionError("A matching, unexpired, one-time rollback approval is required.")
        fd, temporary = tempfile.mkstemp(prefix=".zexa-rollback-", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, target.stat().st_mode & 0o777)
            os.replace(temporary, target)
        except Exception:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        return {
            "status": "rolled_back",
            "path": payload["path"],
            "restored_sha256": payload["restore_sha256"],
        }
