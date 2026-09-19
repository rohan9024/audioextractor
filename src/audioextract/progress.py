"""Parsing helpers for FFmpeg's machine-readable progress stream."""
from __future__ import annotations

from .models import ProgressUpdate


def parse_timestamp(value: str) -> float | None:
    """Convert FFmpeg HH:MM:SS.microseconds timestamps to seconds."""
    try:
        hours, minutes, seconds = value.split(":", maxsplit=2)
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, TypeError):
        return None


def progress_from_record(
    record: dict[str, str], total_duration: float | None
) -> ProgressUpdate:
    out_seconds = None
    if "out_time" in record:
        out_seconds = parse_timestamp(record["out_time"])

    percent = None
    if out_seconds is not None and total_duration and total_duration > 0:
        percent = max(0.0, min(100.0, (out_seconds / total_duration) * 100.0))

    state = record.get("progress", "continue")
    if state == "end" and percent is not None:
        percent = 100.0

    return ProgressUpdate(
        state=state,
        out_time_seconds=out_seconds,
        percent=percent,
        speed=record.get("speed"),
    )
