from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .config import AddonConfig, DisplayWindow


class ArtWindowManager:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config
        self.timezone = ZoneInfo(config.timezone)

    def should_show_schedule(self, moment: datetime | None = None) -> bool:
        moment = moment or datetime.now(self.timezone)
        local_time = moment.astimezone(self.timezone).time()
        return any(in_window(local_time, window) for window in self.config.display_windows)

    def today_bounds(self, moment: datetime | None = None) -> tuple[datetime, datetime]:
        moment = moment or datetime.now(self.timezone)
        today = moment.astimezone(self.timezone).date()
        start = datetime.combine(today, time.min, tzinfo=self.timezone)
        end = datetime.combine(today, time.max, tzinfo=self.timezone)
        return start, end


def in_window(value: time, window: DisplayWindow) -> bool:
    start = parse_time(window.start)
    end = parse_time(window.end)
    if start <= end:
        return start <= value < end
    return value >= start or value < end


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))
