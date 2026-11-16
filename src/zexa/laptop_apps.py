"""Owner-configured allowlist for narrowly scoped laptop application launching."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess


_APP_ID = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_MAX_MANIFEST_BYTES = 64_000
_MAX_APPS = 30


class LaptopAppRegistry:
    """Launch only fixed executable/argument pairs selected by the laptop owner."""

    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path).expanduser()
        if (
            self.manifest_path.is_symlink()
            or not self.manifest_path.is_file()
            or self.manifest_path.stat().st_size > _MAX_MANIFEST_BYTES
        ):
            raise PermissionError("Laptop app manifest must be a bounded regular file, not a symlink.")
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Laptop app manifest must be valid UTF-8 JSON.") from exc
        if not isinstance(data, dict) or set(data) != {"version", "apps"} or data["version"] != 1:
            raise ValueError("Unsupported laptop app manifest format.")
        apps = data["apps"]
        if not isinstance(apps, list) or not 1 <= len(apps) <= _MAX_APPS:
            raise ValueError("Laptop app manifest must contain 1–30 approved applications.")
        self._apps: dict[str, dict] = {}
        for item in apps:
            if not isinstance(item, dict) or set(item) != {"id", "executable", "arguments", "description"}:
                raise ValueError("Each approved app needs exactly id, executable, arguments, and description.")
            app_id = item["id"]
            executable = item["executable"]
            arguments = item["arguments"]
            description = item["description"]
            if not isinstance(app_id, str) or not _APP_ID.fullmatch(app_id):
                raise ValueError("Laptop app IDs must use lowercase letters, digits, dots, underscores, or hyphens.")
            if app_id in self._apps:
                raise ValueError("Laptop app IDs must be unique.")
            if not isinstance(executable, str) or not executable or len(executable) > 1024:
                raise ValueError("Approved app executable path is invalid.")
            executable_path = Path(executable).expanduser()
            if (
                not executable_path.is_absolute() or executable_path.is_symlink()
                or not executable_path.is_file()
            ):
                raise ValueError("Approved app executable must be an existing absolute regular file, not a symlink.")
            if (
                not isinstance(arguments, list) or len(arguments) > 16
                or any(
                    not isinstance(value, str) or len(value) > 256
                    or any(ord(char) < 32 or ord(char) == 127 for char in value)
                    for value in arguments
                )
            ):
                raise ValueError("Approved app arguments must be a bounded list of plain strings.")
            if not isinstance(description, str) or not description.strip() or len(description) > 200:
                raise ValueError("Approved app description must contain 1–200 characters.")
            self._apps[app_id] = {
                "executable": str(executable_path.resolve(strict=True)),
                "arguments": tuple(arguments),
                "description": description.strip(),
            }

    def list_apps(self) -> list[dict[str, str]]:
        return [
            {"app_id": app_id, "description": item["description"]}
            for app_id, item in sorted(self._apps.items())
        ]

    def launch(self, app_id: str) -> dict[str, str | bool]:
        if not isinstance(app_id, str) or app_id not in self._apps:
            raise KeyError("Laptop app is not in the owner's approved launch list.")
        item = self._apps[app_id]
        command = [item["executable"], *item["arguments"]]
        options = {}
        if os.name != "nt":
            options["start_new_session"] = True
        try:
            process = subprocess.Popen(
                command,
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                **options,
            )
        except OSError as exc:
            raise RuntimeError("The approved laptop application could not be started.") from exc
        return {"app_id": app_id, "spawned": True, "process_id": str(process.pid)}
