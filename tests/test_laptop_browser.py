from __future__ import annotations

import unittest
from unittest.mock import patch

from zexa.laptop_browser import open_browser_url, validate_browser_url


class LaptopBrowserTests(unittest.TestCase):
    def test_validates_and_normalizes_public_https_url(self):
        self.assertEqual(
            validate_browser_url("HTTPS://Example.COM/docs?q=one#section"),
            "https://example.com/docs?q=one#section",
        )
        self.assertEqual(
            validate_browser_url("https://[2606:4700:4700::1111]/"),
            "https://[2606:4700:4700::1111]/",
        )

    def test_rejects_non_https_credentials_local_and_nonstandard_ports(self):
        for value in (
            "http://example.com", "javascript:alert(1)",
            "https://user:pass@example.com", "https://localhost",
            "https://printer.local", "https://127.0.0.1",
            "https://192.168.1.10", "https://example.com:8443",
            "https://example.com/space here", "https://example.com\\nHost: evil",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_browser_url(value)

    def test_opens_only_validated_url_in_visible_default_browser(self):
        with patch("zexa.laptop_browser.webbrowser.open", return_value=True) as browser:
            result = open_browser_url("https://example.com/docs")
        self.assertEqual(result, {"opened": True, "host": "example.com"})
        browser.assert_called_once_with(
            "https://example.com/docs", new=2, autoraise=True
        )

    def test_reports_browser_open_failure(self):
        with patch("zexa.laptop_browser.webbrowser.open", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "did not report"):
                open_browser_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
