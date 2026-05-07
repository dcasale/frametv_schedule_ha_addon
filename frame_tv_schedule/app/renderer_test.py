from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from .calendar_client import CalendarEvent, WeatherForecast
from .config import AddonConfig
from .renderer import ScheduleRenderer, strip_emoji, visible_weather_forecasts, weather_rain_label


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
                    CalendarEvent("calendar.family", "Lunch", datetime(2026, 5, 4, 12, 0, tzinfo=zone), datetime(2026, 5, 4, 13, 0, tzinfo=zone), False, "A longer location that should have enough vertical room to wrap cleanly"),
                ],
                now=datetime(2026, 5, 4, 7, 0, tzinfo=zone),
                weather=[
                    WeatherForecast(datetime(2026, 5, 4, 8, 0, tzinfo=zone), condition="rainy", temperature=61, precipitation_probability=45),
                    WeatherForecast(datetime(2026, 5, 4, 9, 0, tzinfo=zone), condition="cloudy", temperature=63, precipitation_probability=20),
                ],
            )

        self.assertEqual(result, path)

    def test_weather_forecasts_are_filtered_and_converted_to_local_time(self) -> None:
        zone = ZoneInfo("America/Los_Angeles")
        utc = ZoneInfo("UTC")
        forecasts = visible_weather_forecasts(
            [
                WeatherForecast(datetime(2026, 5, 4, 13, 0, tzinfo=utc), condition="cloudy", temperature=60, precipitation_probability=10),
                WeatherForecast(datetime(2026, 5, 4, 14, 0, tzinfo=utc), condition="rainy", temperature=61, precipitation_probability=45),
            ],
            now=datetime(2026, 5, 4, 7, 20, tzinfo=zone),
            timezone=zone,
        )

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0].datetime, datetime(2026, 5, 4, 7, 0, tzinfo=zone))

    def test_weather_rain_label_uses_precipitation_fallback(self) -> None:
        self.assertEqual(
            weather_rain_label(WeatherForecast(datetime=None, condition="", temperature=None, precipitation_probability=45)),
            "45% rain",
        )
        self.assertEqual(
            weather_rain_label(WeatherForecast(datetime=None, condition="", temperature=None, precipitation_probability=None, precipitation=0.2)),
            "0.2 rain",
        )

    def test_strip_emoji_removes_unsupported_calendar_symbols(self) -> None:
        self.assertEqual(strip_emoji("Birthday 🎂 bus 🚌"), "Birthday bus")


if __name__ == "__main__":
    unittest.main()
