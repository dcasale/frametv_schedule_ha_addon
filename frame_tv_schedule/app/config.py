from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class DisplayWindow(BaseModel):
    start: str
    end: str


class AddonConfig(BaseModel):
    calendar_entities: list[str] = Field(default_factory=list)
    timezone: str = "America/Los_Angeles"
    image_width: int = 3840
    image_height: int = 2160
    refresh_minutes: int = 30
    generate_time: str = "05:00"
    display_windows: list[DisplayWindow] = Field(default_factory=list)
    restore_mode: Literal["previous_art", "fallback_art", "none"] = "previous_art"
    fallback_art_id: str = ""
    fallback_image: str = ""
    tv_host: str = ""
    tv_name: str = "Frame TV"
    push_mode: Literal["dry_run", "local_frame_api", "home_assistant_service"] = "dry_run"
    weather_entity: str = ""
    privacy_mode: bool = False


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
