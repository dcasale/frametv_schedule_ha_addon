from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from .calendar_client import CalendarEvent
from .config import AddonConfig
from .renderer import ScheduleRenderer


class RendererTest(unittest.TestCase):
    def test_renders_large_schedule_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "schedule.png"
            config = AddonConfig(image_width=1920, image_height=1080)
            renderer = ScheduleRenderer(config, output_path=path)
            zone = ZoneInfo(config.timezone)

            result = renderer.render(
                [
                    CalendarEvent("calendar.family", "Morning appointment with a longer readable title", datetime(2026, 5, 4, 8, 30, tzinfo=zone), datetime(2026, 5, 4, 9, 30, tzinfo=zone), False),
                    CalendarEvent("calendar.family", "Lunch", datetime(2026, 5, 4, 12, 0, tzinfo=zone), datetime(2026, 5, 4, 13, 0, tzinfo=zone), False),
                ],
                now=datetime(2026, 5, 4, 7, 0, tzinfo=zone),
            )

        self.assertEqual(result, path)


if __name__ == "__main__":
    unittest.main()
