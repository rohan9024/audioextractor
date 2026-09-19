"""Media inspection using ffprobe."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from ._utils import resolve_ffprobe
from .exceptions import ProbeError
from .models import MediaInfo, MediaStream


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def probe_media(
    path: Path,
    *,
    ffprobe_path: str | Path | None = None,
    timeout: float = 15.0,
) -> MediaInfo:
    """Inspect a local media file without loading its contents into Python memory."""
    binary = resolve_ffprobe(ffprobe_path)
    cmd = [
        binary,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]

    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"ffprobe exceeded {timeout:.1f}s for {path.name}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "ffprobe returned no diagnostic output"
        raise ProbeError(f"Unable to inspect {path.name}: {detail}")

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"ffprobe returned invalid JSON for {path.name}") from exc

    streams: list[MediaStream] = []
    for raw in payload.get("streams", []):
        streams.append(
            MediaStream(
                index=_to_int(raw.get("index")) or 0,
                codec_type=str(raw.get("codec_type") or "unknown"),
                codec_name=raw.get("codec_name"),
                sample_rate=_to_int(raw.get("sample_rate")),
                channels=_to_int(raw.get("channels")),
                channel_layout=raw.get("channel_layout"),
            )
        )

    fmt = payload.get("format", {})
    duration = _to_float(fmt.get("duration"))
    size = _to_int(fmt.get("size")) or path.stat().st_size

    return MediaInfo(
        path=path,
        size_bytes=size,
        duration_seconds=duration,
        format_name=fmt.get("format_name"),
        streams=tuple(streams),
    )
