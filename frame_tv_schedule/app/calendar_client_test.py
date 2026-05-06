from __future__ import annotations

import unittest
from datetime import datetime

from .calendar_client import parse_calendar_events, parse_weather_forecasts, weather_forecast_types, websocket_url


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

    def test_parse_weather_forecasts_accepts_alternate_provider_fields(self) -> None:
        forecasts = parse_weather_forecasts(
            "weather.forecast_home",
            {
                "service_response": {
                    "weather.forecast_home": {
                        "forecast": [
                            {
                                "datetime": "2026-05-05T14:00:00+00:00",
                                "condition": "partlycloudy",
                                "native_temperature": "68",
                                "probability_of_precipitation": "35%",
                            }
                        ]
                    }
                }
            },
        )

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0].temperature, 68.0)
        self.assertEqual(forecasts[0].precipitation_probability, 35)

    def test_parse_weather_forecasts_empty_error_shape(self) -> None:
        forecasts = parse_weather_forecasts("weather.home", {"message": "Internal Server Error"})

        self.assertEqual(forecasts, [])

    def test_websocket_url_from_api_url(self) -> None:
        self.assertEqual(websocket_url("http://127.0.0.1:8123/api"), "ws://127.0.0.1:8123/api/websocket")
        self.assertEqual(websocket_url("https://ha.example.test/api"), "wss://ha.example.test/api/websocket")

    def test_weather_forecast_types(self) -> None:
        self.assertEqual(weather_forecast_types("hourly"), ["hourly"])
        self.assertEqual(weather_forecast_types("auto"), ["hourly", "daily", "twice_daily"])


if __name__ == "__main__":
    unittest.main()
