import tempfile
import unittest
from pathlib import Path

from .thumbnail_cache import archive_orphan_thumbnails


class ArchiveOrphanThumbnailsTest(unittest.TestCase):
    def test_moves_only_thumbnails_missing_from_tv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            archive = Path(directory) / "archive"
            cache.mkdir()
            (cache / "SAM-F0103.jpg").write_bytes(b"keep")
            (cache / "MY_F0007.jpg").write_bytes(b"gone")

            moved = archive_orphan_thumbnails(cache, archive, {"SAM-F0103"})

            self.assertEqual(moved, [archive / "MY_F0007.jpg"])
            self.assertEqual(
                sorted(path.name for path in cache.iterdir()), ["SAM-F0103.jpg"]
            )
            self.assertEqual((archive / "MY_F0007.jpg").read_bytes(), b"gone")

    def test_never_overwrites_an_archived_thumbnail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "cache"
            archive = Path(directory) / "archive"
            cache.mkdir()
            archive.mkdir()
            (archive / "MY_F0007.jpg").write_bytes(b"first")
            (cache / "MY_F0007.jpg").write_bytes(b"second")

            archive_orphan_thumbnails(cache, archive, set())

            self.assertEqual((archive / "MY_F0007.jpg").read_bytes(), b"first")
            self.assertEqual((archive / "MY_F0007-2.jpg").read_bytes(), b"second")


if __name__ == "__main__":
    unittest.main()
