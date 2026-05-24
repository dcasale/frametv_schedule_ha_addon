from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .config import AddonConfig, DisplayWindow


class ArtWindowManager:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config
        self.timezone = ZoneInfo(config.timezone)

    def should_show_schedule(self, moment: datetime | None = None) -> bool:
        moment = moment or datetime.now(self.timezone)
        local_moment = moment.astimezone(self.timezone)
        local_time = local_moment.time()
        return any(in_window(local_time, window) for window in self.active_display_windows_for(local_moment))

    def is_window_start(self, moment: datetime | None = None) -> bool:
        moment = moment or datetime.now(self.timezone)
        local_moment = moment.astimezone(self.timezone)
        local_time = local_moment.time()
        return any(same_hour_minute(local_time, parse_time(window.start)) for window in self.display_windows_for(local_moment))

    def today_bounds(self, moment: datetime | None = None) -> tuple[datetime, datetime]:
        moment = moment or datetime.now(self.timezone)
        today = moment.astimezone(self.timezone).date()
        start = datetime.combine(today, time.min, tzinfo=self.timezone)
        end = datetime.combine(today, time.max, tzinfo=self.timezone)
        return start, end

    def display_windows_for(self, moment: datetime | date) -> list[DisplayWindow]:
        local_date = moment.date() if isinstance(moment, datetime) else moment
        if is_weekend(local_date):
            return self.config.weekend_display_windows
        return self.config.display_windows

    def active_display_windows_for(self, moment: datetime) -> list[DisplayWindow]:
        local_date = moment.date()
        local_time = moment.time()
        windows = [window for window in self.display_windows_for(local_date) if not wraps_midnight(window) or local_time >= parse_time(window.start)]
        previous_date = local_date - timedelta(days=1)
        windows.extend(window for window in self.display_windows_for(previous_date) if wraps_midnight(window) and local_time < parse_time(window.end))
        return windows

    def schedule_boundary_times(self) -> list[time]:
        boundaries: list[time] = []
        for window in [*self.config.display_windows, *self.config.weekend_display_windows]:
            boundaries.append(parse_time(window.start))
            boundaries.append(parse_time(window.end))
        return sorted(unique_times(boundaries))


def in_window(value: time, window: DisplayWindow) -> bool:
    start = parse_time(window.start)
    end = parse_time(window.end)
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def wraps_midnight(window: DisplayWindow) -> bool:
    return parse_time(window.start) > parse_time(window.end)


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def same_hour_minute(left: time, right: time) -> bool:
    return left.hour == right.hour and left.minute == right.minute


def is_weekend(value: date) -> bool:
    return value.weekday() >= 5


def unique_times(values: list[time]) -> list[time]:
    seen: set[tuple[int, int]] = set()
    unique: list[time] = []
    for value in values:
        key = (value.hour, value.minute)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def generated_today(state: dict[str, Any], moment: datetime, timezone: ZoneInfo) -> bool:
    last_generated = state.get("last_generated")
    if not isinstance(last_generated, str) or not last_generated:
        return False
    try:
        generated_at = datetime.fromisoformat(last_generated)
    except ValueError:
        return False
    return generated_at.astimezone(timezone).date() == moment.astimezone(timezone).date()
