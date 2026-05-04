from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DisplayWindow(BaseModel):
    start: str
    end: str


class AddonConfig(BaseModel):
    calendar_entity: str = ""
    additional_calendar_entity_1: str = ""
    additional_calendar_entity_2: str = ""
    calendar_entities: list[str] = Field(default_factory=list)
    timezone: str = "America/Los_Angeles"
    image_width: int = 3840
    image_height: int = 2160
    refresh_minutes: int = 30
    generate_time: str = "05:00"
    morning_window_start: str = "06:00"
    morning_window_end: str = "08:00"
    afternoon_window_start: str = "14:30"
    afternoon_window_end: str = "16:30"
    display_windows: list[DisplayWindow] = Field(default_factory=list)
    restore_mode: Literal["previous_art", "fallback_art", "none"] = "previous_art"
    fallback_art_id: str = ""
    fallback_image: str = ""
    tv_host: str = ""
    tv_port: int = 8002
    tv_name: str = "Frame TV"
    tv_token_file: str = "/config/samsung-frame-token.txt"
    tv_timeout_seconds: int = 15
    tv_matte: str = "none"
    push_mode: Literal["dry_run", "local_frame_api", "home_assistant_service"] = "dry_run"
    weather_entity: str = ""
    privacy_mode: bool = False
    ignore_art_support_check: bool = False

    @model_validator(mode="after")
    def apply_simple_fields(self) -> "AddonConfig":
        simple_calendar_entities = [
            self.calendar_entity,
            self.additional_calendar_entity_1,
            self.additional_calendar_entity_2,
        ]
        simple_calendar_entities = [entity.strip() for entity in simple_calendar_entities if entity.strip()]
        if simple_calendar_entities:
            self.calendar_entities = simple_calendar_entities

        simple_windows = [
            DisplayWindow(start=self.morning_window_start, end=self.morning_window_end),
            DisplayWindow(start=self.afternoon_window_start, end=self.afternoon_window_end),
        ]
        if not self.display_windows:
            self.display_windows = simple_windows
        return self


def load_config(path: str | Path = "/data/options.json") -> AddonConfig:
    options_path = Path(path)
    if options_path.exists():
        return AddonConfig.model_validate_json(options_path.read_text())

    fallback = os.environ.get("FRAME_TV_SCHEDULE_OPTIONS")
    if fallback:
        return AddonConfig.model_validate_json(fallback)

    return AddonConfig()


def config_json(config: AddonConfig) -> str:
    return json.dumps(config.model_dump(), indent=2)
