from __future__ import annotations

from pathlib import Path


def archive_orphan_thumbnails(
    cache_dir: Path, archive_dir: Path, current_stems: set[str]
) -> list[Path]:
    """Move cached thumbnails for art no longer on the TV out of the live cache.

    They are kept, not deleted: after art is lost on the TV they may be the only
    record of it. Moving them also stops a reused art ID (the TV restarts MY_F
    numbering after a reset) from showing an old image for new art.
    """
    moved: list[Path] = []
    for path in sorted(cache_dir.iterdir()):
        if not path.is_file() or path.stem in current_stems:
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / path.name
        index = 2
        while target.exists():
            target = archive_dir / f"{path.stem}-{index}{path.suffix}"
            index += 1
        path.rename(target)
        moved.append(target)
    return moved
