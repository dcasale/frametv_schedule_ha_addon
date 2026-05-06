from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import os
from typing import Any
from zoneinfo import ZoneInfo

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
        self.timezone = ZoneInfo(config.timezone)
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
                entity_events = parse_calendar_events(entity, data, self.timezone)
                logger.info("calendar fetch returned calendar=%s event_count=%s", entity, len(entity_events))
                events.extend(entity_events)

        logger.info("calendar fetch total event_count=%s", len(events))
        sort_fallback = datetime.max.replace(tzinfo=self.timezone)
        return sorted(events, key=lambda event: event.start or sort_fallback)

    async def get_hourly_weather(self, weather_entity: str, limit: int = 24) -> list[WeatherForecast]:
        weather_entity = weather_entity.strip()
        if not weather_entity:
            return []
        if not self.base_url or not self.token:
            logger.warning("skipping weather fetch because the Home Assistant API token is unavailable")
            return []

        forecast_types = weather_forecast_types(self.config.weather_forecast_type)
        for forecast_type in forecast_types:
            try:
                data = await self._fetch_weather_forecasts_websocket(weather_entity, forecast_type)
                forecasts = parse_weather_forecasts(weather_entity, data)
                logger.info(
                    "weather websocket fetch returned entity=%s type=%s forecast_count=%s",
                    weather_entity,
                    forecast_type,
                    len(forecasts),
                )
                if forecasts:
                    return forecasts[:limit]
            except Exception:
                logger.exception("weather websocket fetch failed entity=%s type=%s", weather_entity, forecast_type)

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            for forecast_type in forecast_types:
                payload = {"entity_id": weather_entity, "type": forecast_type}
                async with session.post(
                    f"{self.base_url}/services/weather/get_forecasts?return_response",
                    json=payload,
                    timeout=30,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        logger.warning(
                            "weather REST fetch failed entity=%s type=%s status=%s response=%s",
                            weather_entity,
                            forecast_type,
                            response.status,
                            text[:500],
                        )
                        continue
                    data = await response.json()
                forecasts = parse_weather_forecasts(weather_entity, data)
                logger.info(
                    "weather REST fetch returned entity=%s type=%s forecast_count=%s",
                    weather_entity,
                    forecast_type,
                    len(forecasts),
                )
                if forecasts:
                    return forecasts[:limit]

        return []

    async def _fetch_weather_forecasts_websocket(self, weather_entity: str, forecast_type: str) -> dict[str, Any]:
        assert self.token
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(websocket_url(self.base_url), timeout=30) as ws:
                auth_required = await ws.receive_json(timeout=30)
                if auth_required.get("type") != "auth_required":
                    raise RuntimeError(f"Unexpected WebSocket auth prompt: {auth_required}")

                await ws.send_json({"type": "auth", "access_token": self.token})
                auth_response = await ws.receive_json(timeout=30)
                if auth_response.get("type") != "auth_ok":
                    raise RuntimeError(f"Home Assistant WebSocket auth failed: {auth_response}")

                await ws.send_json(
                    {
                        "id": 1,
                        "type": "call_service",
                        "domain": "weather",
                        "service": "get_forecasts",
                        "service_data": {"type": forecast_type},
                        "target": {"entity_id": weather_entity},
                        "return_response": True,
                    }
                )
                response = await ws.receive_json(timeout=30)

        if not response.get("success"):
            raise RuntimeError(f"Home Assistant weather service failed: {response}")
        result = response.get("result") or {}
        return {"service_response": result.get("response") or {}}

    async def debug_weather_fetch(self, weather_entity: str) -> dict[str, Any]:
        weather_entity = weather_entity.strip()
        result: dict[str, Any] = {
            "entity": weather_entity,
            "configured_forecast_type": self.config.weather_forecast_type,
            "attempts": [],
        }
        if not weather_entity:
            result["error"] = "No weather entity is configured"
            return result
        if not self.base_url or not self.token:
            result["error"] = "Home Assistant API token is unavailable"
            return result

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self.base_url}/states/{weather_entity}", timeout=30) as response:
                result["state_status"] = response.status
                if response.status < 400:
                    state = await response.json()
                    result["state"] = state.get("state")
                    attributes = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
                    result["friendly_name"] = attributes.get("friendly_name")
                    result["supported_features"] = attributes.get("supported_features")
                else:
                    result["state_error"] = (await response.text())[:500]

        for forecast_type in weather_forecast_types(self.config.weather_forecast_type):
            attempt: dict[str, Any] = {"type": forecast_type}
            try:
                data = await self._fetch_weather_forecasts_websocket(weather_entity, forecast_type)
                forecasts = parse_weather_forecasts(weather_entity, data)
                attempt["forecast_count"] = len(forecasts)
                attempt["sample_forecasts"] = [weather_to_debug_dict(forecast) for forecast in forecasts[:5]]
                attempt["raw_keys"] = list(data.keys())
            except Exception as error:
                attempt["error"] = f"{type(error).__name__}: {error}"
            result["attempts"].append(attempt)
        return result

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
                    events = parse_calendar_events(entity, data, self.timezone)
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


def parse_calendar_events(
    calendar: str,
    data: list[dict[str, Any]] | dict[str, Any],
    timezone: ZoneInfo | None = None,
) -> list[CalendarEvent]:
    if isinstance(data, dict):
        raw_events = extract_raw_events(data)
    else:
        raw_events = data

    events: list[CalendarEvent] = []
    for item in raw_events:
        start = parse_ha_datetime(item.get("start"), timezone)
        end = parse_ha_datetime(item.get("end"), timezone)
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


def weather_to_debug_dict(forecast: WeatherForecast) -> dict[str, Any]:
    return {
        "datetime": forecast.datetime.isoformat() if forecast.datetime else None,
        "condition": forecast.condition,
        "temperature": forecast.temperature,
        "precipitation_probability": forecast.precipitation_probability,
        "precipitation": forecast.precipitation,
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
                temperature=coerce_number(first_present(item, "temperature", "native_temperature")),
                precipitation_probability=coerce_int(
                    first_present(
                        item,
                        "precipitation_probability",
                        "probability_of_precipitation",
                        "precipitation_chance",
                        "rain_probability",
                        "chance_of_rain",
                        "pop",
                    )
                ),
                precipitation=coerce_number(first_present(item, "precipitation", "native_precipitation", "rain")),
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
        clean = value.strip().removesuffix("%").strip()
        try:
            return round(float(clean))
        except ValueError:
            return None
    return None


def coerce_number(value: Any) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        clean = value.strip().removesuffix("%").strip()
        try:
            return float(clean)
        except ValueError:
            return None
    return None


def first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def websocket_url(base_url: str) -> str:
    if base_url.startswith("https://"):
        return base_url.replace("https://", "wss://", 1).rstrip("/") + "/websocket"
    if base_url.startswith("http://"):
        return base_url.replace("http://", "ws://", 1).rstrip("/") + "/websocket"
    return base_url.rstrip("/") + "/websocket"


def weather_forecast_types(configured_type: str) -> list[str]:
    if configured_type in {"hourly", "daily", "twice_daily"}:
        return [configured_type]
    return ["hourly", "daily", "twice_daily"]


def parse_ha_datetime(value: str | dict[str, str] | None, timezone: ZoneInfo | None = None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, dict):
        value = value.get("dateTime") or value.get("date")
    if not value:
        return None

    parsed = datetime.fromisoformat(value)
    if not timezone:
        return parsed
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone)
    return parsed.astimezone(timezone)


def is_all_day_value(value: str | dict[str, str] | None) -> bool:
    if isinstance(value, dict):
        return "date" in value and "dateTime" not in value
    return bool(value and "T" not in value)
