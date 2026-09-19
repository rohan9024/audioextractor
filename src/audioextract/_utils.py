"""Private utility helpers."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

from .exceptions import FFmpegNotFoundError, FFprobeNotFoundError, InvalidInputError


def resolve_ffmpeg(explicit_path: str | Path | None = None) -> str:
    if explicit_path is not None:
        path = Path(explicit_path).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise FFmpegNotFoundError(f"FFmpeg not found at: {path}")

    found = shutil.which("ffmpeg")
    if not found:
        raise FFmpegNotFoundError(
            "FFmpeg was not found on PATH. Install FFmpeg and try again."
        )
    return found


def resolve_ffprobe(explicit_path: str | Path | None = None) -> str:
    if explicit_path is not None:
        path = Path(explicit_path).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise FFprobeNotFoundError(f"ffprobe not found at: {path}")

    found = shutil.which("ffprobe")
    if not found:
        raise FFprobeNotFoundError(
            "ffprobe was not found on PATH. It is normally installed with FFmpeg."
        )
    return found


def validate_source(source: str | Path) -> Path:
    path = Path(source).expanduser().resolve()
    if not path.exists():
        raise InvalidInputError(f"File not found: {path}")
    if not path.is_file():
        raise InvalidInputError(f"Not a file: {path}")
    if path.stat().st_size <= 0:
        raise InvalidInputError(f"File is empty: {path}")
    return path


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def temporary_output_path(target: Path) -> Path:
    return target.parent / f".{target.stem}.{uuid4().hex}.partial{target.suffix}"


def safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def atomic_replace(source: Path, target: Path) -> None:
    os.replace(source, target)
