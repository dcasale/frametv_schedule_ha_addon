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

    def test_should_show_schedule_uses_weekend_windows_on_weekends(self) -> None:
        config = AddonConfig(
            timezone="America/Los_Angeles",
            morning_window_start="06:00",
            morning_window_end="08:00",
            weekend_morning_window_start="09:00",
            weekend_morning_window_end="11:00",
        )
        manager = ArtWindowManager(config)

        self.assertFalse(manager.should_show_schedule(datetime(2026, 5, 9, 7, 0, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertTrue(manager.should_show_schedule(datetime(2026, 5, 9, 9, 30, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertTrue(manager.should_show_schedule(datetime(2026, 5, 11, 7, 0, tzinfo=ZoneInfo("America/Los_Angeles"))))

    def test_overnight_weekday_window_continues_after_midnight_on_weekend(self) -> None:
        config = AddonConfig(
            timezone="America/Los_Angeles",
            morning_window_start="23:00",
            morning_window_end="01:00",
            weekend_morning_window_start="09:00",
            weekend_morning_window_end="11:00",
        )
        manager = ArtWindowManager(config)

        self.assertTrue(manager.should_show_schedule(datetime(2026, 5, 8, 23, 30, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertTrue(manager.should_show_schedule(datetime(2026, 5, 9, 0, 30, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertFalse(manager.should_show_schedule(datetime(2026, 5, 9, 1, 0, tzinfo=ZoneInfo("America/Los_Angeles"))))

    def test_is_window_start_matches_start_minute(self) -> None:
        config = AddonConfig(timezone="America/Los_Angeles", morning_window_start="06:00", morning_window_end="08:00")
        manager = ArtWindowManager(config)

        self.assertTrue(manager.is_window_start(datetime(2026, 5, 5, 6, 0, 30, tzinfo=ZoneInfo("America/Los_Angeles"))))
        self.assertFalse(manager.is_window_start(datetime(2026, 5, 5, 6, 1, tzinfo=ZoneInfo("America/Los_Angeles"))))

    def test_schedule_boundary_times_include_weekday_and_weekend_windows(self) -> None:
        config = AddonConfig(
            morning_window_start="06:00",
            morning_window_end="08:00",
            weekend_morning_window_start="09:00",
            weekend_morning_window_end="11:00",
        )
        manager = ArtWindowManager(config)

        self.assertEqual(
            [value.strftime("%H:%M") for value in manager.schedule_boundary_times()],
            ["06:00", "08:00", "09:00", "11:00", "14:30", "16:30"],
        )

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
