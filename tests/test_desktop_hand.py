"""Tests for the approval-gated desktop Human Hand."""
import unittest

from zexa.desktop import DesktopHand


class DesktopHandTests(unittest.TestCase):
    def test_status_is_read_only_and_reports_disabled_capabilities(self):
        status = DesktopHand.status()
        self.assertEqual(status["mode"], "approval_gated")
        self.assertFalse(status["screen_capture"])
        self.assertFalse(status["keyboard_monitoring"])
        self.assertFalse(status["shell_execution"])

    def test_validates_and_opens_https_only_after_approval(self):
        calls = []
        hand = DesktopHand(opener=lambda url, **kwargs: calls.append((url, kwargs)) or True)
        result = hand.open_url(
            " https://example.com/path ",
            approve=lambda action, payload: action == "open_url" and payload["url"] == "https://example.com/path",
        )
        self.assertEqual(result, {"action": "open_url", "url": "https://example.com/path", "opened": True})
        self.assertEqual(calls, [("https://example.com/path", {"new": 2, "autoraise": False})])

    def test_rejects_missing_or_denied_approval_without_opening(self):
        calls = []
        hand = DesktopHand(opener=lambda *args, **kwargs: calls.append(args) or True)
        with self.assertRaises(PermissionError):
            hand.open_url("https://example.com")
        with self.assertRaises(PermissionError):
            hand.open_url("https://example.com", approve=lambda *_: False)
        self.assertEqual(calls, [])

    def test_rejects_unsafe_or_malformed_urls(self):
        for url in (
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,hello",
            "https://user:pass@example.com",
            "https://example.com:99999",
            "https:///missing-host",
            "",
            "x" * 2049,
        ):
            with self.subTest(url=url[:40]), self.assertRaises((TypeError, ValueError)):
                DesktopHand.validate_url(url)

    def test_does_not_report_success_when_browser_does_not_confirm(self):
        hand = DesktopHand(opener=lambda *_args, **_kwargs: False)
        with self.assertRaisesRegex(RuntimeError, "did not confirm"):
            hand.open_url("https://example.com", approve=lambda *_: True)


if __name__ == "__main__":
    unittest.main()
