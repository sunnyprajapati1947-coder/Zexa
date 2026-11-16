from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from zexa import cli


class FakeStore:
    def __init__(self, permissions):
        self.permissions = permissions

    def get(self, host, port, client_id):
        return {
            "fingerprint": "a" * 64,
            "permissions": self.permissions,
            "session_key_b64": "must-not-be-displayed",
        }


class FakeLaptopClient:
    instance = None

    def __init__(self, host, port, fingerprint, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.store = FakeStore((
            "laptop.workspace.list", "laptop.workspace.read", "laptop.workspace.write",
            "laptop.apps.launch", "laptop.browser.open", "laptop.browser.read",
        ))
        self.writes = []
        self.launches = []
        self.browser_opens = []
        self.page_reads = []
        FakeLaptopClient.instance = self

    def open_browser_url(self, url, *, user_confirmed=False):
        self.browser_opens.append((url, user_confirmed))
        return {"opened": True, "host": "example.com"}

    def read_public_page(self, url):
        self.page_reads.append(url)
        return {"title": "Example", "url": url, "text": "Page text", "content_sha256": "a" * 64, "content_trust": "untrusted_reference"}

    def list_apps(self):
        return [{"app_id": "editor", "description": "Approved editor"}]

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

    def test_laptop_owner_can_list_and_revoke_paired_clients(self):
        authority = Mock()
        authority.list_clients.return_value = [{
            "client_id": "phone-main", "paired_at_epoch": 123,
            "permissions": ["laptop.workspace.read"],
        }]
        authority.revoke_client.return_value = True
        with (
            patch("sys.argv", [
                "zexa", "laptop", "clients", "--pairings", "/tmp/pairings.sqlite3"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopPairingAuthority", return_value=authority),
            patch("builtins.print"),
        ):
            cli.main()
        authority.list_clients.assert_called_once_with()

        authority.reset_mock()
        authority.revoke_client.return_value = True
        with (
            patch("sys.argv", [
                "zexa", "laptop", "revoke-client", "phone-main",
                "--pairings", "/tmp/pairings.sqlite3",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopPairingAuthority", return_value=authority),
            patch.object(cli, "AuditLog") as audit,
            patch.object(cli, "secure_owner_only"),
            patch("builtins.print"),
        ):
            cli.main()
        authority.revoke_client.assert_called_once_with("phone-main")
        audit.return_value.record.assert_called_once()

    def test_laptop_status_shows_pairing_metadata_without_session_secret(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "status", "--host", "192.168.1.20"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.print") as output,
        ):
            cli.main()
        import json
        status = json.loads(output.call_args.args[0])
        self.assertTrue(status["paired"])
        self.assertEqual(status["host"], "192.168.1.20")
        self.assertEqual(status["client_id"], "zexa-phone")
        self.assertIn("laptop.workspace.read", status["permissions"])
        self.assertNotIn("session_key_b64", status)
        self.assertNotIn("must-not-be-displayed", output.call_args.args[0])

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

    def test_laptop_apps_command_lists_owner_allowlisted_apps(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "apps", "--host", "192.168.1.20"
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.print") as output,
        ):
            cli.main()
        output.assert_called_once()

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

    def test_laptop_browser_open_requires_exact_confirmation(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "open-url", "--host", "192.168.1.20",
                "https://example.com/docs",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="OPEN URL https://example.com/docs"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(
            FakeLaptopClient.instance.browser_opens,
            [("https://example.com/docs", True)],
        )

    def test_laptop_browser_open_cancel_sends_no_request(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "open-url", "--host", "192.168.1.20",
                "https://example.com/docs",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="no"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(FakeLaptopClient.instance.browser_opens, [])

    def test_laptop_browser_open_checks_scope_before_prompting(self):
        class ReadOnlyLaptopClient(FakeLaptopClient):
            def __init__(self, host, port, fingerprint, client_id):
                super().__init__(host, port, fingerprint, client_id)
                self.store.permissions = ("laptop.workspace.list", "laptop.workspace.read")

        with (
            patch("sys.argv", [
                "zexa", "laptop", "open-url", "--host", "192.168.1.20",
                "https://example.com/docs",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", ReadOnlyLaptopClient),
            patch("builtins.input") as prompt,
            patch("builtins.print"),
        ):
            with self.assertRaisesRegex(PermissionError, "lacks laptop browser permission"):
                cli.main()
        prompt.assert_not_called()

    def test_server_requires_opt_in_for_browser_navigation(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("sys.argv", [
                "zexa", "laptop", "serve", "--host", "192.168.1.20",
                "--workspace", temp, "--cert", str(Path(temp) / "cert.pem"),
                "--key", str(Path(temp) / "key.pem"), "--allow-browser-open",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopWorkspace"),
            patch.object(cli, "LaptopAgentServer") as server,
            patch.object(cli, "certificate_fingerprint", return_value="a" * 64),
        ):
            server.return_value.begin_pairing.return_value = Mock(
                pairing_code="123456789012", expires_in_seconds=120,
                permissions=("laptop.browser.open",),
            )
            server.return_value.serve_forever.side_effect = KeyboardInterrupt
            cli.main()
        server.return_value.begin_pairing.assert_called_once_with(
            permissions=["laptop.workspace.list", "laptop.workspace.read", "laptop.browser.open"]
        )

    def test_laptop_read_url_requires_exact_confirmation_and_scope(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "read-url", "--host", "192.168.1.20",
                "https://example.com/article",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="READ URL https://example.com/article"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(
            FakeLaptopClient.instance.page_reads, ["https://example.com/article"]
        )

    def test_laptop_read_url_cancel_sends_no_request(self):
        with (
            patch("sys.argv", [
                "zexa", "laptop", "read-url", "--host", "192.168.1.20",
                "https://example.com/article",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", FakeLaptopClient),
            patch("builtins.input", return_value="no"),
            patch("builtins.print"),
        ):
            cli.main()
        self.assertEqual(FakeLaptopClient.instance.page_reads, [])

    def test_laptop_read_url_checks_scope_before_prompting(self):
        class NoPageReadClient(FakeLaptopClient):
            def __init__(self, host, port, fingerprint, client_id):
                super().__init__(host, port, fingerprint, client_id)
                self.store.permissions = ("laptop.workspace.list", "laptop.workspace.read")

        with (
            patch("sys.argv", [
                "zexa", "laptop", "read-url", "--host", "192.168.1.20",
                "https://example.com/article",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopAgentClient", NoPageReadClient),
            patch("builtins.input") as prompt,
            patch("builtins.print"),
        ):
            with self.assertRaisesRegex(PermissionError, "lacks laptop page-read permission"):
                cli.main()
        prompt.assert_not_called()

    def test_laptop_server_can_opt_in_to_public_page_reading(self):
        with (
            tempfile.TemporaryDirectory() as temp,
            patch("sys.argv", [
                "zexa", "laptop", "serve", "--host", "192.168.1.20",
                "--workspace", temp, "--cert", str(Path(temp) / "cert.pem"),
                "--key", str(Path(temp) / "key.pem"), "--allow-browser-read",
            ]),
            patch.object(cli, "load_env_file"),
            patch.object(cli, "LaptopWorkspace"),
            patch.object(cli, "LaptopAgentServer") as server,
            patch.object(cli, "certificate_fingerprint", return_value="a" * 64),
        ):
            server.return_value.begin_pairing.return_value = Mock(
                pairing_code="123456789012", expires_in_seconds=120,
                permissions=("laptop.workspace.list", "laptop.workspace.read", "laptop.browser.read"),
            )
            server.return_value.serve_forever.side_effect = KeyboardInterrupt
            cli.main()
        server.return_value.begin_pairing.assert_called_once_with(
            permissions=["laptop.workspace.list", "laptop.workspace.read", "laptop.browser.read"]
        )

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
