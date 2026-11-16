from __future__ import annotations

import unittest
from unittest.mock import patch

from zexa.laptop_browser import open_browser_url, read_public_page, validate_browser_url\nfrom zexa.research import FetchedPage


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

    def test_reads_only_bounded_public_page_text_and_preserves_provenance(self):
        page = FetchedPage(
            "Example title", "https://example.com/article",
            "Extracted public text.", "a" * 64,
        )
        with patch("zexa.laptop_browser.fetch_public_page", return_value=page) as fetch:
            result = read_public_page("https://example.com/article")
        self.assertEqual(result, {
            "title": "Example title",
            "url": "https://example.com/article",
            "text": "Extracted public text.",
            "content_sha256": "a" * 64,
        })
        fetch.assert_called_once_with("https://example.com/article")

    def test_rejects_empty_or_oversized_page_text(self):
        for text in (" ", "x" * 40_001):
            page = FetchedPage("Example", "https://example.com", text, "b" * 64)
            with patch("zexa.laptop_browser.fetch_public_page", return_value=page):
                with self.assertRaisesRegex(RuntimeError, "readable text"):
                    read_public_page("https://example.com")

    def test_reports_browser_open_failure(self):
        with patch("zexa.laptop_browser.webbrowser.open", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "did not report"):
                open_browser_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
