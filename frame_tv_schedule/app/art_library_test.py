from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from .art_library import ArtLibrary, sanitize_name, unique_name


class ArtLibraryTest(unittest.TestCase):
    def test_unique_name_and_sanitize_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            self.assertEqual(unique_name(directory, "Family Photo.jpg"), "Family-Photo.png")
            (directory / "Family-Photo.png").write_text("")
            self.assertEqual(unique_name(directory, "Family Photo.jpg"), "Family-Photo-2.png")

        self.assertEqual(sanitize_name("../art.png"), "art.png")
        self.assertEqual(sanitize_name("art"), "art.png")

    def test_list_images_returns_pngs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            (directory / "b.png").write_text("")
            (directory / "a.png").write_text("")
            (directory / "ignored.jpg").write_text("")

            library = ArtLibrary(directory)

            self.assertEqual([path.name for path in library.list_images()], ["a.png", "b.png"])

    def test_delete_removes_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            path = directory / "art.png"
            path.write_text("")

            library = ArtLibrary(directory)
            deleted = library.delete("art.png")

            self.assertEqual(deleted, path)
            self.assertFalse(path.exists())

    def test_normalizes_image_to_target_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            source = directory / "source.jpg"
            Image.new("RGB", (1200, 800), "#336699").save(source)

            library = ArtLibrary(directory, width=1920, height=1080)
            target = directory / "target.png"
            from .art_library import normalize_image

            normalize_image(source, target, 1920, 1080)

            with Image.open(target) as image:
                self.assertEqual(image.size, (1920, 1080))


if __name__ == "__main__":
    unittest.main()
