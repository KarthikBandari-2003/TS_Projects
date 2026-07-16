import tempfile
import unittest
from pathlib import Path

from modules.button_detector import ButtonDetector
from modules.logger import ToolLogger


class ButtonDetectorTests(unittest.TestCase):
    def test_matches_target_aliases(self):
        self.assertTrue(ButtonDetector.matches_target("OK", "button_ok"))
        self.assertTrue(ButtonDetector.matches_target("YES", "button_yes"))
        self.assertTrue(ButtonDetector.matches_target("Accept", "ok"))
        self.assertTrue(ButtonDetector.matches_target("Continue", "yes"))

    def test_non_matching_targets(self):
        self.assertFalse(ButtonDetector.matches_target("OK", "cancel"))
        self.assertFalse(ButtonDetector.matches_target("YES", "menu"))


class LoggerDashboardTests(unittest.TestCase):
    def test_logger_forwards_messages_to_dashboard(self):
        class FakeDashboard:
            def __init__(self):
                self.messages = []

            def append(self, message, level="INFO"):
                self.messages.append((message, level))

        with tempfile.TemporaryDirectory() as tmpdir:
            dashboard = FakeDashboard()
            logger = ToolLogger(tmpdir, tmpdir, dashboard=dashboard)
            try:
                logger.info("hello dashboard")
                self.assertTrue(any(message == "hello dashboard" for message, _ in dashboard.messages))
            finally:
                logger.close()


if __name__ == "__main__":
    unittest.main()
