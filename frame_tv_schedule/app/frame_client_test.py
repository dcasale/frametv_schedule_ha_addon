from pathlib import Path
import tempfile
import unittest

from .frame_client import available_art_items, available_content_ids, extract_content_id, file_sha256


class FrameClientHelpersTest(unittest.TestCase):
    def test_extract_content_id_from_common_payloads(self) -> None:
        self.assertEqual(extract_content_id("MY-F0001"), "MY-F0001")
        self.assertEqual(extract_content_id({"content_id": "MY-F0002"}), "MY-F0002")
        self.assertEqual(extract_content_id({"event": {"contentId": "MY-F0003"}}), "MY-F0003")

    def test_available_content_ids_handles_wrapped_lists(self) -> None:
        payload = {"items": [{"content_id": "MY-F0001"}, {"contentId": "MY-F0002"}]}
        self.assertEqual(available_content_ids(payload), {"MY-F0001", "MY-F0002"})

    def test_available_art_items_extracts_ids_and_titles(self) -> None:
        payload = {"items": [{"content_id": "MY-F0001", "title": "Landscape"}, {"contentId": "MY-F0002", "fileName": "Portrait"}]}
        items = available_art_items(payload)
        self.assertEqual([item.art_id for item in items], ["MY-F0001", "MY-F0002"])
        self.assertEqual([item.title for item in items], ["Landscape", "Portrait"])

    def test_file_sha256_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.png"
            path.write_bytes(b"schedule")
            self.assertEqual(file_sha256(path), file_sha256(path))


if __name__ == "__main__":
    unittest.main()
