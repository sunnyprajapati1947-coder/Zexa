import unittest

from zexa.android import TermuxAndroidHand


class AndroidHandTests(unittest.TestCase):
    def test_notification_uses_fixed_command_without_shell(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))

        hand = TermuxAndroidHand(
            which=lambda name: "/fake/termux-notification",
            run=fake_run,
        )
        hand.notify("Zexa", "Build complete")
        self.assertEqual(
            calls[0][0],
            ["/fake/termux-notification", "--title", "Zexa", "--content", "Build complete"],
        )
        self.assertTrue(calls[0][1]["check"])
        self.assertEqual(calls[0][1]["timeout"], 10)

    def test_notification_rejects_empty_text(self):
        hand = TermuxAndroidHand(which=lambda name: "/fake/termux-notification", run=lambda *a, **k: None)
        with self.assertRaises(ValueError):
            hand.notify("", "message")

    def test_notification_rejects_missing_capability(self):
        hand = TermuxAndroidHand(which=lambda name: None, run=lambda *a, **k: None)
        with self.assertRaises(RuntimeError):
            hand.notify("Zexa", "message")


    def test_torch_uses_fixed_on_off_command_without_shell(self):
        calls = []
        hand = TermuxAndroidHand(
            which=lambda name: "/fake/termux-torch" if name == "termux-torch" else None,
            run=lambda command, **kwargs: calls.append((command, kwargs)),
        )
        hand.set_torch("on")
        hand.set_torch("off")
        self.assertEqual(calls[0][0], ["/fake/termux-torch", "on"])
        self.assertEqual(calls[1][0], ["/fake/termux-torch", "off"])
        self.assertTrue(calls[0][1]["check"])

    def test_torch_rejects_invalid_state_and_missing_capability(self):
        hand = TermuxAndroidHand(which=lambda name: None, run=lambda *a, **k: None)
        with self.assertRaises(ValueError):
            hand.set_torch("toggle")
        with self.assertRaises(RuntimeError):
            hand.set_torch("on")


if __name__ == "__main__":
    unittest.main()
