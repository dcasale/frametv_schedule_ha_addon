from __future__ import annotations

from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from .art_window_manager import ArtWindowManager, in_window
from .config import AddonConfig, DisplayWindow


class ArtWindowManagerTest(unittest.TestCase):
    def test_window_end_is_exclusive(self) -> None:
        window = DisplayWindow(start="06:00", end="08:00")

        self.assertTrue(in_window(datetime(2026, 5, 5, 7, 59).time(), window))
        self.assertFalse(in_window(datetime(2026, 5, 5, 8, 0).time(), window))

    def test_should_show_schedule_uses_configured_timezone(self) -> None:
        config = AddonConfig(timezone="America/Los_Angeles", morning_window_start="06:00", morning_window_end="08:00")
        manager = ArtWindowManager(config)

        self.assertTrue(manager.should_show_schedule(datetime(2026, 5, 5, 14, 30, tzinfo=ZoneInfo("UTC"))))
        self.assertFalse(manager.should_show_schedule(datetime(2026, 5, 5, 15, 0, tzinfo=ZoneInfo("UTC"))))


if __name__ == "__main__":
    unittest.main()
