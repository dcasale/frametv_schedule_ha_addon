from __future__ import annotations

from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from .art_window_manager import ArtWindowManager, generated_today, in_window
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

    def test_is_window_start_matches_start_minute(self) -> None:
        config = AddonConfig(timezone="America/Los_Angeles", morning_window_start="06:00", morning_window_end="08:00")
        manager = ArtWindowManager(config)

        self.assertTrue(manager.is_window_start(datetime(2026, 5, 5, 6, 0, 30, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertFalse(manager.is_window_start(datetime(2026, 5, 5, 6, 1, tzinfo=ZoneInfo("America/Los_Angeles"))))

    def test_generated_today_uses_local_timezone(self) -> None:
        zone = ZoneInfo("America/Los_Angeles")

        self.assertTrue(
            generated_today(
                {"last_generated": "2026-05-06T05:00:00-07:00"},
                datetime(2026, 5, 6, 6, 0, tzinfo=zone),
                zone,
            )
        )
        self.assertFalse(
            generated_today(
                {"last_generated": "2026-05-05T23:00:00-07:00"},
                datetime(2026, 5, 6, 6, 0, tzinfo=zone),
                zone,
            )
        )


if __name__ == "__main__":
    unittest.main()
