import unittest
from unittest.mock import patch

from zexa.android import AndroidCapabilityProbe


class AndroidCapabilityTests(unittest.TestCase):
    def test_probe_reports_available_commands_without_running_them(self):
        def fake_which(command):
            return "/fake/" + command if command == "termux-notification" else None

        report = AndroidCapabilityProbe(which=fake_which).as_dict()
        self.assertEqual(report["platform"], "android-termux")
        self.assertEqual(report["mode"], "read_only_detection")
        self.assertFalse(report["actions_executed"])
        self.assertEqual(report["available_count"], 1)
        notification = next(
            item for item in report["capabilities"]
            if item["name"] == "notification"
        )
        self.assertTrue(notification["available"])

    def test_probe_checks_all_capabilities(self):
        with patch("zexa.android.shutil.which", return_value=None) as which:
            report = AndroidCapabilityProbe(which=which).as_dict()
        self.assertEqual(report["available_count"], 0)
        self.assertEqual(which.call_count, 7)


if __name__ == "__main__":
    unittest.main()
