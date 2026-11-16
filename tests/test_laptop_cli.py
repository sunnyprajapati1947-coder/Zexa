from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zexa import cli


class FakeStore:
    def __init__(self, permissions):
        self.permissions = permissions

    def get(self, host, port, client_id):
        return {"permissions": self.permissions}


class FakeLaptopClient:
    instance = None

    def __init__(self, host, port, fingerprint, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.store = FakeStore((
            "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write",
            "laptop.apps.launch",
        ))
        self.writes = []
        self.launches = []
        FakeLaptopClient.instance = self

    def launch_app(self, app_id, *, user_confirmed=False):
        self.launches.append((app_id, user_confirmed))
        return {"app_id": app_id, "spawned": True}

    def write_text(self, path, content, *, overwrite=False, user_confirmed=False):
        self.writes.append((path, content, overwrite, user_confirmed))
        return {"relative_path": path, "written": True}


class LaptopCliTests(unittest.TestCase):
    def invoke_write(self, source, destination, confirmation, *extra):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "write", "--host", "192.168.1.20",
                *extra, str(source), destination,
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value=confirmation),
            patch("builtins.print"),
        ):
            cli.main()
        return FakeLaptopClient.instance

    def test_server_refuses_app_launch_without_owner_manifest(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("sys.argv", [
                "zexa", "laptop", "serve", "--host", "192.168.1.20",
                "--workspace", temp, "--cert", str(Path(temp) / "cert.pem"),
                "--key", str(Path(temp) / "key.pem"), "--allow-app-launch",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopWorkspace"),
            patch.object(cli, "LaptopAgentServer") as server,
        ):
            with self.assertRaisesRegex(ValueError, "--apps manifest"):
                cli.main()
        server.assert_not_called()

    def test_laptop_app_launch_requires_exact_confirmation(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "launch", "--host", "192.168.1.20", "editor"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="LAUNCH editor"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(FakeLaptopClient.instance.launches, [("editor", True)])

    def test_laptop_app_launch_checks_scope_before_prompting(self):
        class ReadOnlyLaptopClient(FakeLaptopClient):
            def __init__(self, host, port, fingerprint, client_id):
                super().__init__(host, port, fingerprint, client_id)
                self.store.permissions = ("laptop.workspace.list", "laptop.workspace.read")

        with (
            patch("sys.argv", [
                "zexa", "laptop", "launch", "--host", "192.168.1.20", "editor"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", ReadOnlyLaptopClient),
            patch("builtins.input") as prompt,
            patch("builtins.print"),
        ):
            with self.assertRaisesRegex(PermissionError, "lacks laptop app-launch permission"):
                cli.main()
        prompt.assert_not_called()

    def test_laptop_app_launch_cancel_sends_no_request(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "launch", "--host", "192.168.1.20", "editor"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="no"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(FakeLaptopClient.instance.launches, [])

    def test_remote_write_cancel_sends_no_data(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "notes.md"
            source.write_text("hello", encoding="utf-8")
            client = self.invoke_write(source, "docs/notes.md", "no")
        self.assertEqual(client.writes, [])

    def test_remote_write_requires_exact_destination_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "notes.md"
            source.write_text("hello", encoding="utf-8")
            client = self.invoke_write(source, "docs/notes.md", "WRITE docs/notes.md")
        self.assertEqual(
            client.writes,
            [("docs/notes.md", "hello", False, True)],
        )

    def test_overwrite_requires_distinct_confirmation(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "notes.md"
            source.write_text("updated", encoding="utf-8")
            client = self.invoke_write(
                source, "docs/notes.md", "WRITE docs/notes.md", "--overwrite"
            )
        self.assertEqual(client.writes, [])

        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "notes.md"
            source.write_text("updated", encoding="utf-8")
            client = self.invoke_write(
                source, "docs/notes.md", "OVERWRITE docs/notes.md", "--overwrite"
            )
        self.assertEqual(
            client.writes,
            [("docs/notes.md", "updated", True, True)],
        )


if __name__ == "__main__":
    unittest.main()
