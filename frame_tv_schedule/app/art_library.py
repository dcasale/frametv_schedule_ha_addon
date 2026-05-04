from __future__ import annotations

import re
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps


class ArtLibrary:
    def __init__(self, path: str | Path = "/config/art-library", width: int = 3840, height: int = 2160) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.width = width
        self.height = height

    def list_images(self) -> list[Path]:
        return sorted(self.path.glob("*.png"), key=lambda item: item.name.lower())

    def get(self, name: str) -> Path:
        safe_name = sanitize_name(name)
        path = self.path / safe_name
        if path.parent != self.path or not path.exists():
            raise FileNotFoundError(f"Art image not found: {name}")
        return path

    async def save_upload(self, upload: UploadFile) -> Path:
        if not upload.filename:
            raise ValueError("Uploaded file needs a filename")

        name = unique_name(self.path, upload.filename)
        output_path = self.path / name
        data = await upload.read()
        if not data:
            raise ValueError("Uploaded file is empty")

        source_path = self.path / f".{name}.upload"
        source_path.write_bytes(data)
        try:
            normalize_image(source_path, output_path, self.width, self.height)
        finally:
            source_path.unlink(missing_ok=True)

        return output_path


def normalize_image(source: Path, target: Path, width: int, height: int) -> None:
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), "#101010")
        x = (width - image.width) // 2
        y = (height - image.height) // 2
        canvas.paste(image, (x, y))
        canvas.save(target, "PNG")


def unique_name(directory: Path, filename: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(filename).stem).strip(".-") or "art"
    candidate = f"{stem}.png"
    index = 2
    while (directory / candidate).exists():
        candidate = f"{stem}-{index}.png"
        index += 1
    return candidate


def sanitize_name(name: str) -> str:
    safe = Path(name).name
    if not safe.endswith(".png"):
        safe = f"{safe}.png"
    return safe
