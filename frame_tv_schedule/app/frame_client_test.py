import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Self

from .frame_client import (
    ArtNotOnTvError,
    FrameClient,
    available_art_items,
    available_content_ids,
    current_art_item,
    extract_content_id,
    file_sha256,
    schedule_art_ids,
    thumbnail_bytes,
)


class FrameClientHelpersTest(unittest.TestCase):
    def test_extract_content_id_from_common_payloads(self) -> None:
        self.assertEqual(extract_content_id("MY-F0001"), "MY-F0001")
        self.assertEqual(extract_content_id({"content_id": "MY-F0002"}), "MY-F0002")
        self.assertEqual(
            extract_content_id({"event": {"contentId": "MY-F0003"}}), "MY-F0003"
        )

    def test_available_content_ids_handles_wrapped_lists(self) -> None:
        payload = {"items": [{"content_id": "MY-F0001"}, {"contentId": "MY-F0002"}]}
        self.assertEqual(available_content_ids(payload), {"MY-F0001", "MY-F0002"})

    def test_available_art_items_extracts_ids_and_titles(self) -> None:
        payload = {
            "items": [
                {"content_id": "MY-F0001", "title": "Landscape"},
                {"contentId": "MY-F0002", "fileName": "Portrait"},
            ]
        }
        items = available_art_items(payload)
        self.assertEqual([item.art_id for item in items], ["MY-F0001", "MY-F0002"])
        self.assertEqual([item.title for item in items], ["Landscape", "Portrait"])

    def test_current_art_item_extracts_id_and_title(self) -> None:
        item = current_art_item(
            {"event": {"contentId": "MY-F0003", "contentName": "Gallery Favorite"}}
        )
        self.assertEqual(item.art_id, "MY-F0003")
        self.assertEqual(item.title, "Gallery Favorite")

    def test_thumbnail_bytes_extracts_common_payloads(self) -> None:
        self.assertEqual(thumbnail_bytes(bytearray(b"abc")), b"abc")
        self.assertEqual(
            thumbnail_bytes({"MY-F0001": bytearray(b"def")}, "MY-F0001"), b"def"
        )
        self.assertEqual(
            thumbnail_bytes({"thumbnail.jpg": bytearray(b"ghi")}, "MY-F0002"), b"ghi"
        )

    def test_file_sha256_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            path.write_bytes(b"schedule")
            self.assertEqual(file_sha256(path), file_sha256(path))

    def test_schedule_art_ids_keep_current_first_and_dedupe_legacy_state(self) -> None:
        state = {
            "schedule_art_id": "OLD-1",
            "schedule_art_ids": ["OLD-2", "OLD-1", "", "OLD-3"],
        }

        self.assertEqual(
            schedule_art_ids(state, current_art_id="CURRENT"),
            ["CURRENT", "OLD-1", "OLD-2", "OLD-3"],
        )


class FakeArt:
    """Stand-in for the samsungtvws art API: select fails with -10 for unknown IDs."""

    def __init__(self, ids: set[str]) -> None:
        self.ids = set(ids)
        self.selected: list[str] = []
        self.uploads = 0

    def supported(self) -> bool:
        return True

    def available(self) -> list[dict[str, str]]:
        return [{"content_id": art_id} for art_id in sorted(self.ids)]

    def select_image(self, art_id: str, show: bool = True) -> None:
        if art_id not in self.ids:
            raise RuntimeError("`select_image` request failed with error number -10")
        self.selected.append(art_id)

    def upload(self, file: bytes, **_: str) -> dict[str, str]:
        self.uploads += 1
        art_id = f"MY_F{100 + self.uploads:04}"
        self.ids.add(art_id)
        return {"content_id": art_id}


class BusyArt(FakeArt):
    def select_image(self, art_id: str, show: bool = True) -> None:
        raise RuntimeError("busy")


class FakeTv:
    def __init__(self, art: FakeArt) -> None:
        self._art = art

    def art(self) -> FakeArt:
        return self._art

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def fake_client(directory: Path, art: FakeArt) -> FrameClient:
    client = FrameClient.__new__(FrameClient)
    client.config = SimpleNamespace(
        tv_host="tv", tv_matte="none", push_mode="local_frame_api"
    )
    client.state_path = directory / "frame-client-state.json"
    client._tv = lambda: FakeTv(art)
    return client


class FrameClientSelectTest(unittest.TestCase):
    def test_select_of_missing_art_raises_art_not_on_tv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = fake_client(Path(directory), FakeArt({"SAM-F0103"}))
            with self.assertRaises(ArtNotOnTvError) as raised:
                client._select_art_sync("MY_F0007")
            self.assertEqual(raised.exception.art_id, "MY_F0007")

    def test_select_failure_for_present_art_is_not_reported_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = fake_client(Path(directory), BusyArt({"MY_F0001"}))
            with self.assertRaisesRegex(RuntimeError, "busy") as raised:
                client._select_art_sync("MY_F0001")
            self.assertNotIsInstance(raised.exception, ArtNotOnTvError)

    def test_show_image_reuploads_when_cached_copy_is_gone(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "Art.png"
            image.write_bytes(b"art")
            art = FakeArt(set())
            client = fake_client(root, art)

            client._show_image_sync(image, label="artwork_Art")
            first_id = art.selected[-1]
            art.ids.discard(first_id)  # deleted on the TV, or the TV was reset
            client._show_image_sync(image, label="artwork_Art")

            self.assertEqual(art.uploads, 2)
            self.assertNotEqual(art.selected[-1], first_id)
            state = json.loads(client.state_path.read_text())
            self.assertEqual(state["artwork_Art_art_id"], art.selected[-1])


if __name__ == "__main__":
    unittest.main()
