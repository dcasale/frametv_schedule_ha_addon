from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import AddonConfig


@dataclass(frozen=True)
class ArtState:
    art_id: str = ""
    source: str = ""


class FrameClient:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config
        self.state_path = Path("/config/frame-client-state.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def get_current_art(self) -> ArtState:
        if self.config.push_mode == "dry_run":
            return ArtState(source="dry_run")

        if self.config.push_mode == "local_frame_api":
            return await asyncio.to_thread(self._get_current_art_sync)

        return ArtState(source="unsupported")

    async def show_schedule(self, image_path: Path) -> None:
        if self.config.push_mode == "dry_run":
            print(f"[frame] dry run: would show {image_path} on {self.config.tv_name}")
            return

        if self.config.push_mode == "local_frame_api":
            await asyncio.to_thread(self._show_schedule_sync, image_path)
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

        if self.config.push_mode == "local_frame_api":
            await asyncio.to_thread(self._restore_art_sync, previous)
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    def _get_current_art_sync(self) -> ArtState:
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            payload = art.get_current()
            content_id = extract_content_id(payload)
            return ArtState(art_id=content_id, source="local_frame_api")

    def _show_schedule_sync(self, image_path: Path) -> None:
        content_id = self._ensure_uploaded_schedule(image_path)
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            art.select_image(content_id, show=True)
            art.set_artmode(True)
        print(f"[frame] showing schedule art {content_id}")

    def _restore_art_sync(self, previous: ArtState | None) -> None:
        target = ""
        if self.config.restore_mode == "previous_art" and previous and previous.art_id:
            target = previous.art_id
        if not target and self.config.fallback_art_id:
            target = self.config.fallback_art_id
        if not target and self.config.fallback_image:
            target = self._ensure_uploaded_fallback(Path(self.config.fallback_image))

        if not target:
            print("[frame] no previous or fallback art available to restore")
            return

        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            art.select_image(target, show=True)
            art.set_artmode(True)
        print(f"[frame] restored art {target}")

    def _ensure_uploaded_schedule(self, image_path: Path) -> str:
        image_hash = file_sha256(image_path)
        state = self._read_state()
        if state.get("schedule_image_sha256") == image_hash and state.get("schedule_art_id"):
            return str(state["schedule_art_id"])

        content_id = self._upload_image(image_path)
        self._write_state({**state, "schedule_image_sha256": image_hash, "schedule_art_id": content_id})
        return content_id

    def _ensure_uploaded_fallback(self, image_path: Path) -> str:
        image_hash = file_sha256(image_path)
        state = self._read_state()
        if state.get("fallback_image_sha256") == image_hash and state.get("fallback_art_id"):
            return str(state["fallback_art_id"])

        content_id = self._upload_image(image_path)
        self._write_state({**state, "fallback_image_sha256": image_hash, "fallback_art_id": content_id})
        return content_id

    def _upload_image(self, image_path: Path) -> str:
        if not image_path.exists():
            raise FileNotFoundError(f"Frame image does not exist: {image_path}")

        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            before = available_content_ids(art.available())
            data = image_path.read_bytes()
            kwargs: dict[str, str] = {"file_type": "png"}
            if self.config.tv_matte and self.config.tv_matte != "none":
                kwargs["matte"] = self.config.tv_matte
            response = art.upload(file=data, **kwargs)
            content_id = extract_content_id(response)
            if not content_id:
                after = available_content_ids(art.available())
                created = sorted(after - before)
                if created:
                    content_id = created[-1]

        if not content_id:
            raise RuntimeError("Samsung Frame upload succeeded but no content ID was returned or detected")

        return content_id

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text())

    def _write_state(self, state: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True))

    def _tv(self) -> "SamsungTvContext":
        if not self.config.tv_host:
            raise RuntimeError("tv_host is required when push_mode is local_frame_api")

        return SamsungTvContext(self.config)


class SamsungTvContext:
    def __init__(self, config: AddonConfig) -> None:
        from samsungtvws import SamsungTVWS

        self.tv = SamsungTVWS(
            host=config.tv_host,
            port=config.tv_port,
            token_file=config.tv_token_file,
            timeout=config.tv_timeout_seconds,
        )

    def __enter__(self) -> Any:
        return self.tv

    def __exit__(self, *_: object) -> None:
        close = getattr(self.tv, "close", None)
        if callable(close):
            close()


def ensure_art_supported(art: Any) -> None:
    supported = getattr(art, "supported", None)
    if callable(supported) and supported() is False:
        raise RuntimeError("This TV does not report Samsung Frame Art Mode API support")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def available_content_ids(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        values = payload.get("items") or payload.get("content") or payload.get("data") or []
    else:
        values = payload

    ids: set[str] = set()
    if isinstance(values, list):
        for item in values:
            content_id = extract_content_id(item)
            if content_id:
                ids.add(content_id)
    return ids


def extract_content_id(payload: Any) -> str:
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for key in ("content_id", "contentId", "id", "image_id", "imageId"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
        for value in payload.values():
            nested = extract_content_id(value)
            if nested:
                return nested

    if isinstance(payload, list):
        for item in payload:
            nested = extract_content_id(item)
            if nested:
                return nested

    return ""
