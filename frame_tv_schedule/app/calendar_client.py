from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import os

import aiohttp

logger = logging.getLogger("frame_tv_schedule.calendar")


@dataclass(frozen=True)
class CalendarEvent:
    calendar: str
    summary: str
    start: datetime | None
    end: datetime | None
    all_day: bool
    location: str = ""


class HomeAssistantCalendarClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get("SUPERVISOR_TOKEN") and "http://supervisor/core/api"
        self.token = os.environ.get("SUPERVISOR_TOKEN")

    async def get_events(
        self,
        calendar_entities: list[str],
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        if not calendar_entities:
            logger.warning("skipping calendar fetch because no calendar entities are configured")
            return []
        if not self.base_url or not self.token:
            logger.warning("skipping calendar fetch because the Home Assistant supervisor token is unavailable")
            return []

        logger.info(
            "fetching calendar events entities=%s start=%s end=%s",
            calendar_entities,
            start.isoformat(),
            end.isoformat(),
        )
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "start_date_time": start.isoformat(),
            "end_date_time": end.isoformat(),
            "entity_id": calendar_entities,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{self.base_url}/services/calendar/get_events?return_response",
                json=payload,
                timeout=30,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        events = self._parse_response(data)
        logger.info("calendar fetch returned calendars=%s event_count=%s", list(data.keys()), len(events))
        return events

    def _parse_response(self, data: dict) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        for calendar, value in data.items():
            for item in value.get("events", []):
                start = parse_ha_datetime(item.get("start"))
                end = parse_ha_datetime(item.get("end"))
                events.append(
                    CalendarEvent(
                        calendar=calendar,
                        summary=item.get("summary", "Busy"),
                        start=start,
                        end=end,
                        all_day=is_all_day_value(item.get("start")),
                        location=item.get("location") or "",
                    )
                )

        return sorted(events, key=lambda event: event.start or datetime.max)


def parse_ha_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def is_all_day_value(value: str | None) -> bool:
    return bool(value and "T" not in value)
