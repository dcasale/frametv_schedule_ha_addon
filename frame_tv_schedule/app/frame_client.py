from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import AddonConfig

logger = logging.getLogger("frame_tv_schedule.frame")


@dataclass(frozen=True)
class TvArtItem:
    art_id: str
    title: str = ""
    thumbnail: str = ""


class FrameClient:
    def __init__(self, config: AddonConfig) -> None:
        self.config = config
        self.state_path = Path("/config/frame-client-state.json")
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    async def show_schedule(self, image_path: Path) -> None:
        await self.show_image(image_path, label="schedule")

    async def show_image(self, image_path: Path, label: str = "image") -> None:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would show %s %s on %s", label, image_path, self.config.tv_name)
            return

        if self.config.push_mode == "local_frame_api":
            logger.info("showing %s on Samsung Frame host=%s image=%s", label, self.config.tv_host, image_path)
            await asyncio.to_thread(self._show_image_sync, image_path, label)
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def list_available_art(self) -> list[TvArtItem]:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would list TV art")
            return []

        if self.config.push_mode == "local_frame_api":
            logger.info("listing Samsung Frame art host=%s", self.config.tv_host)
            return await asyncio.to_thread(self._list_available_art_sync)

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def current_art(self) -> TvArtItem:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would read current TV art")
            return TvArtItem(art_id="", title="Dry run")

        if self.config.push_mode == "local_frame_api":
            logger.info("reading current Samsung Frame art host=%s", self.config.tv_host)
            return await asyncio.to_thread(self._current_art_sync)

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def select_art(self, art_id: str) -> None:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would select TV art id=%s", art_id)
            return

        if self.config.push_mode == "local_frame_api":
            logger.info("selecting Samsung Frame art host=%s art_id=%s", self.config.tv_host, art_id)
            await asyncio.to_thread(self._select_art_sync, art_id)
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def delete_art(self, art_id: str) -> None:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would delete TV art id=%s", art_id)
            return

        if self.config.push_mode == "local_frame_api":
            logger.info("deleting Samsung Frame art host=%s art_id=%s", self.config.tv_host, art_id)
            await asyncio.to_thread(self._delete_art_sync, art_id)
            return

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    async def fetch_art_thumbnails(self, art_ids: list[str]) -> dict[str, bytes]:
        if self.config.push_mode == "dry_run":
            logger.info("dry run: would fetch %s TV art thumbnail(s)", len(art_ids))
            return {}

        if self.config.push_mode == "local_frame_api":
            logger.info("fetching %s Samsung Frame thumbnail(s) host=%s", len(art_ids), self.config.tv_host)
            return await asyncio.to_thread(self._fetch_art_thumbnails_sync, art_ids)

        raise NotImplementedError(f"push_mode={self.config.push_mode} is not implemented yet")

    def _show_image_sync(self, image_path: Path, label: str = "image") -> None:
        content_id = self._ensure_uploaded_image(image_path, label)
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            art.select_image(content_id, show=True)
            art.set_artmode(True)
        logger.info("showing %s art id=%s", label, content_id)

    def _list_available_art_sync(self) -> list[TvArtItem]:
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            payload = art.available()
        items = available_art_items(payload)
        logger.info("listed %s Samsung Frame art item(s)", len(items))
        return items

    def _current_art_sync(self) -> TvArtItem:
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            payload = current_art_payload(art)
        item = current_art_item(payload)
        logger.info("current Samsung Frame art id=%s title=%s", item.art_id or "(unknown)", item.title or "(none)")
        return item

    def _select_art_sync(self, art_id: str) -> None:
        if not art_id:
            raise RuntimeError("art_id is required")
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            art.select_image(art_id, show=True)
            art.set_artmode(True)
        logger.info("selected Samsung Frame art id=%s", art_id)

    def _delete_art_sync(self, art_id: str) -> None:
        if not art_id:
            raise RuntimeError("art_id is required")
        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            deleted = art.delete(art_id)
        if deleted is False:
            raise RuntimeError(f"Samsung Frame did not confirm deletion for art id={art_id}")
        logger.info("deleted Samsung Frame art id=%s", art_id)

    def _fetch_art_thumbnails_sync(self, art_ids: list[str]) -> dict[str, bytes]:
        thumbnails: dict[str, bytes] = {}
        if not art_ids:
            return thumbnails

        with self._tv() as tv:
            art = tv.art()
            ensure_art_supported(art)
            for art_id in art_ids:
                payload: Any = None
                thumbnail_list = getattr(art, "get_thumbnail_list", None)
                if callable(thumbnail_list):
                    try:
                        payload = thumbnail_list(art_id)
                    except Exception:
                        logger.exception("failed to fetch Samsung Frame thumbnail list art_id=%s", art_id)
                if not payload:
                    try:
                        payload = art.get_thumbnail(art_id, as_dict=True)
                    except Exception:
                        logger.exception("failed to fetch Samsung Frame thumbnail art_id=%s", art_id)
                        continue
                data = thumbnail_bytes(payload, art_id)
                if data:
                    thumbnails[art_id] = data

        logger.info("fetched %s/%s Samsung Frame thumbnail(s)", len(thumbnails), len(art_ids))
        return thumbnails

    def _ensure_uploaded_schedule(self, image_path: Path) -> str:
        return self._ensure_uploaded_image(image_path, "schedule")

    def _ensure_uploaded_image(self, image_path: Path, label: str) -> str:
        image_hash = file_sha256(image_path)
        state = self._read_state()
        sha_key = f"{label}_image_sha256"
        art_key = f"{label}_art_id"
        if state.get(sha_key) == image_hash and state.get(art_key):
            logger.info("using cached %s art id=%s", label, state[art_key])
            return str(state[art_key])

        content_id = self._upload_image(image_path)
        logger.info("uploaded %s image as art id=%s", label, content_id)
        self._write_state({**state, sha_key: image_hash, art_key: content_id})
        return content_id

    def _upload_image(self, image_path: Path) -> str:
        if not image_path.exists():
            raise FileNotFoundError(f"Frame image does not exist: {image_path}")

        logger.info("uploading image to Samsung Frame host=%s path=%s", self.config.tv_host, image_path)
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


def available_art_items(payload: Any) -> list[TvArtItem]:
    values = art_payload_items(payload)
    items: list[TvArtItem] = []
    for item in values:
        content_id = extract_content_id(item)
        if content_id:
            items.append(TvArtItem(art_id=content_id, title=extract_art_title(item)))
    return sorted(dedupe_art_items(items), key=lambda item: item.title or item.art_id)


def current_art_item(payload: Any) -> TvArtItem:
    return TvArtItem(art_id=extract_content_id(payload), title=extract_art_title(payload))


def current_art_payload(art: Any) -> Any:
    for method_name in ("get_current", "current", "get_current_image", "get_selected"):
        method = getattr(art, method_name, None)
        if callable(method):
            return method()
    raise RuntimeError("Samsung Frame Art Mode API did not expose a current art method")


def art_payload_items(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        values = payload.get("items") or payload.get("content") or payload.get("data") or payload.get("available") or []
    else:
        values = payload
    return values if isinstance(values, list) else []


def dedupe_art_items(items: list[TvArtItem]) -> list[TvArtItem]:
    seen: set[str] = set()
    unique: list[TvArtItem] = []
    for item in items:
        if item.art_id in seen:
            continue
        seen.add(item.art_id)
        unique.append(item)
    return unique


def extract_art_title(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("title", "name", "file_name", "fileName", "content_name", "contentName"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    for value in payload.values():
        nested = extract_art_title(value)
        if nested:
            return nested
    return ""


def thumbnail_bytes(payload: Any, art_id: str = "") -> bytes:
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    if isinstance(payload, dict):
        if art_id and isinstance(payload.get(art_id), (bytes, bytearray)):
            return bytes(payload[art_id])
        for value in payload.values():
            if isinstance(value, (bytes, bytearray)):
                return bytes(value)
    if isinstance(payload, list):
        for value in payload:
            if isinstance(value, (bytes, bytearray)):
                return bytes(value)
    return b""


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
