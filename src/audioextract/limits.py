"""Pre-flight safety checks."""
from __future__ import annotations

from .exceptions import MediaLimitError, NoAudioStreamError
from .models import ExtractionOptions, MediaInfo


def enforce_limits(media: MediaInfo, options: ExtractionOptions) -> None:
    if not media.audio_streams:
        raise NoAudioStreamError(f"No audio stream found in {media.path.name}")

    if options.audio_stream_index >= len(media.audio_streams):
        raise NoAudioStreamError(
            f"Requested audio stream {options.audio_stream_index}, but "
            f"{media.path.name} only contains {len(media.audio_streams)} audio stream(s)."
        )

    if (
        options.max_file_size_bytes is not None
        and media.size_bytes > options.max_file_size_bytes
    ):
        raise MediaLimitError(
            f"Input is {media.size_bytes} bytes, exceeding the configured "
            f"limit of {options.max_file_size_bytes} bytes."
        )

    if (
        options.max_duration_seconds is not None
        and media.duration_seconds is not None
        and media.duration_seconds > options.max_duration_seconds
    ):
        raise MediaLimitError(
            f"Input duration is {media.duration_seconds:.2f}s, exceeding the configured "
            f"limit of {options.max_duration_seconds:.2f}s."
        )
