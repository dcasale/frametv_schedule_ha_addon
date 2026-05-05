from __future__ import annotations

import unittest
from datetime import datetime

from .calendar_client import parse_calendar_events, parse_weather_forecasts


class CalendarClientTest(unittest.TestCase):
    def test_parse_rest_calendar_events(self) -> None:
        events = parse_calendar_events(
            "calendar.family",
            [
                {
                    "summary": "Breakfast",
                    "start": {"dateTime": "2026-05-03T07:30:00-07:00"},
                    "end": {"dateTime": "2026-05-03T08:00:00-07:00"},
                    "location": "Kitchen",
                },
                {
                    "summary": "All day reminder",
                    "start": {"date": "2026-05-03"},
                    "end": {"date": "2026-05-04"},
                },
            ],
        )

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].summary, "Breakfast")
        self.assertEqual(events[0].start, datetime.fromisoformat("2026-05-03T07:30:00-07:00"))
        self.assertFalse(events[0].all_day)
        self.assertEqual(events[0].location, "Kitchen")
        self.assertEqual(events[1].summary, "All day reminder")
        self.assertTrue(events[1].all_day)

    def test_parse_wrapped_service_response_events(self) -> None:
        events = parse_calendar_events(
            "calendar.family",
            {
                "service_response": {
                    "calendar.family": {
                        "events": [
                            {
                                "summary": "Appointment",
                                "start": "2026-05-03T09:00:00-07:00",
                                "end": "2026-05-03T10:00:00-07:00",
                            }
                        ]
                    }
                }
            },
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].summary, "Appointment")

    def test_parse_weather_forecasts(self) -> None:
        forecasts = parse_weather_forecasts(
            "weather.home",
            {
                "service_response": {
                    "weather.home": {
                        "forecast": [
                            {
                                "datetime": "2026-05-05T10:00:00-07:00",
                                "condition": "rainy",
                                "temperature": 62.4,
                                "precipitation_probability": 40,
                            }
                        ]
                    }
                }
            },
        )

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0].condition, "rainy")
        self.assertEqual(forecasts[0].temperature, 62.4)
        self.assertEqual(forecasts[0].precipitation_probability, 40)


if __name__ == "__main__":
    unittest.main()
