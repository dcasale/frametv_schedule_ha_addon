from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import AddonConfig


@dataclass(frozen=True)
class ArtState:
    art_id: str = ""
    source: str = ""


class FrameClient:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config

    async def get_current_art(self) -> ArtState:
        return ArtState(source="unsupported")

    async def show_schedule(self, image_path: Path) -> None:
        if self.config.push_mode == "dry_run":
            print(f"[frame] dry run: would show {image_path} on {self.config.tv_name}")
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def restore_art(self, previous: ArtState | None = None) -> None:
        if self.config.restore_mode == "none":
            print("[frame] restore disabled")
            return

        if self.config.push_mode == "dry_run":
            target = previous.art_id if previous and previous.art_id else self.config.fallback_art_id
            print(f"[frame] dry run: would restore art {target or '(unknown)'}")
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")
