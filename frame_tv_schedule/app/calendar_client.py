from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import os
from typing import Any

import aiohttp

from .config import AddonConfig

logger = logging.getLogger("frame_tv_schedule.calendar")


@dataclass(frozen=True)
class CalendarEvent:
    calendar: str
    summary: str
    start: datetime | None
    end: datetime | None
    all_day: bool
    location: str = ""


@dataclass(frozen=True)
class WeatherForecast:
    datetime: datetime | None
    condition: str
    temperature: float | int | None
    precipitation_probability: int | None
    precipitation: float | int | None = None


def supervisor_token() -> str:
    return os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN") or ""


class HomeAssistantCalendarClient:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config
        self.token = config.home_assistant_token.strip() or supervisor_token()
        self.base_url = config.home_assistant_url.rstrip("/") if config.home_assistant_token.strip() else self.token and "http://supervisor/core/api"
        logger.info(
            "Home Assistant API token available=%s manual_token_configured=%s base_url=%s env_has_supervisor_token=%s env_has_hassio_token=%s",
            bool(self.token),
            bool(config.home_assistant_token.strip()),
            self.base_url or "(not set)",
            bool(os.environ.get("SUPERVISOR_TOKEN")),
            bool(os.environ.get("HASSIO_TOKEN")),
        )

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
        events: list[CalendarEvent] = []
        async with aiohttp.ClientSession(headers=headers) as session:
            for entity in calendar_entities:
                data = await self._fetch_rest_events(session, entity, start, end)
                entity_events = parse_calendar_events(entity, data)
                logger.info("calendar fetch returned calendar=%s event_count=%s", entity, len(entity_events))
                events.extend(entity_events)

        logger.info("calendar fetch total event_count=%s", len(events))
        return sorted(events, key=lambda event: event.start or datetime.max)

    async def get_hourly_weather(self, weather_entity: str, limit: int = 8) -> list[WeatherForecast]:
        weather_entity = weather_entity.strip()
        if not weather_entity:
            return []
        if not self.base_url or not self.token:
            logger.warning("skipping weather fetch because the Home Assistant API token is unavailable")
            return []

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"entity_id": weather_entity, "type": "hourly"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{self.base_url}/services/weather/get_forecasts?return_response",
                json=payload,
                timeout=30,
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    logger.warning(
                        "weather fetch failed entity=%s status=%s response=%s",
                        weather_entity,
                        response.status,
                        text[:500],
                    )
                    return []
                data = await response.json()

        forecasts = parse_weather_forecasts(weather_entity, data)
        logger.info("weather fetch returned entity=%s forecast_count=%s", weather_entity, len(forecasts))
        return forecasts[:limit]

    async def debug_calendar_fetch(
        self,
        calendar_entities: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        if not self.base_url or not self.token:
            return {
                "error": "Home Assistant supervisor token is unavailable",
                "manual_token_configured": bool(self.config.home_assistant_token.strip()),
                "home_assistant_url": self.config.home_assistant_url,
                "env_has_supervisor_token": bool(os.environ.get("SUPERVISOR_TOKEN")),
                "env_has_hassio_token": bool(os.environ.get("HASSIO_TOKEN")),
            }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        result: dict[str, Any] = {"entities": calendar_entities, "start": start.isoformat(), "end": end.isoformat(), "calendars": []}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self.base_url}/calendars", timeout=30) as response:
                result["calendar_list_status"] = response.status
                result["calendar_list"] = await response.json()

            details = []
            for entity in calendar_entities:
                detail: dict[str, Any] = {"entity": entity}
                try:
                    data = await self._fetch_rest_events(session, entity, start, end)
                    events = parse_calendar_events(entity, data)
                    detail["event_count"] = len(events)
                    detail["sample_events"] = [event_to_debug_dict(event) for event in events[:5]]
                    detail["raw_type"] = type(data).__name__
                    detail["raw_keys"] = list(data.keys()) if isinstance(data, dict) else []
                    detail["raw_count"] = len(data) if isinstance(data, list) else None
                except Exception as error:
                    detail["error"] = f"{type(error).__name__}: {error}"
                details.append(detail)
            result["calendars"] = details
        return result

    async def _fetch_rest_events(
        self,
        session: aiohttp.ClientSession,
        entity: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        async with session.get(
            f"{self.base_url}/calendars/{entity}",
            params={"start": start.isoformat(), "end": end.isoformat()},
            timeout=30,
        ) as response:
            response.raise_for_status()
            data = await response.json()
        logger.info(
            "calendar raw response calendar=%s type=%s count=%s keys=%s",
            entity,
            type(data).__name__,
            len(data) if isinstance(data, list) else None,
            list(data.keys()) if isinstance(data, dict) else [],
        )
        return data


def parse_calendar_events(calendar: str, data: list[dict[str, Any]] | dict[str, Any]) -> list[CalendarEvent]:
    if isinstance(data, dict):
        raw_events = extract_raw_events(data)
    else:
        raw_events = data

    events: list[CalendarEvent] = []
    for item in raw_events:
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

    return events


def extract_raw_events(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data.get("events"), list):
        return data["events"]
    if isinstance(data.get("service_response"), dict):
        response = data["service_response"]
        if isinstance(response.get("events"), list):
            return response["events"]
        for value in response.values():
            if isinstance(value, dict) and isinstance(value.get("events"), list):
                return value["events"]
    for value in data.values():
        if isinstance(value, dict) and isinstance(value.get("events"), list):
            return value["events"]
    return []


def event_to_debug_dict(event: CalendarEvent) -> dict[str, Any]:
    return {
        "calendar": event.calendar,
        "summary": event.summary,
        "start": event.start.isoformat() if event.start else None,
        "end": event.end.isoformat() if event.end else None,
        "all_day": event.all_day,
        "location": event.location,
    }


def parse_weather_forecasts(weather_entity: str, data: dict[str, Any]) -> list[WeatherForecast]:
    forecast_items = extract_weather_forecast_items(weather_entity, data)
    forecasts: list[WeatherForecast] = []
    for item in forecast_items:
        if not isinstance(item, dict):
            continue
        forecasts.append(
            WeatherForecast(
                datetime=parse_ha_datetime(item.get("datetime")),
                condition=str(item.get("condition", "")),
                temperature=item.get("temperature") if isinstance(item.get("temperature"), (int, float)) else None,
                precipitation_probability=coerce_int(item.get("precipitation_probability")),
                precipitation=item.get("precipitation") if isinstance(item.get("precipitation"), (int, float)) else None,
            )
        )
    return forecasts


def extract_weather_forecast_items(weather_entity: str, data: dict[str, Any]) -> list[dict[str, Any]]:
    response = data.get("service_response") if isinstance(data.get("service_response"), dict) else data
    entity_value = response.get(weather_entity) if isinstance(response, dict) else None
    if isinstance(entity_value, dict) and isinstance(entity_value.get("forecast"), list):
        return entity_value["forecast"]
    if isinstance(response, dict):
        for value in response.values():
            if isinstance(value, dict) and isinstance(value.get("forecast"), list):
                return value["forecast"]
    return []


def coerce_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    if isinstance(value, str):
        try:
            return round(float(value))
        except ValueError:
            return None
    return None


def parse_ha_datetime(value: str | dict[str, str] | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("dateTime") or value.get("date")
    return datetime.fromisoformat(value) if value else None


def is_all_day_value(value: str | dict[str, str] | None) -> bool:
    if isinstance(value, dict):
        return "date" in value and "dateTime" not in value
    return bool(value and "T" not in value)
