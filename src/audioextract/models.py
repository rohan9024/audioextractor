"""Public data models used by audioextract."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .constants import DEFAULT_CHANNELS, DEFAULT_SAMPLE_RATE, SUPPORTED_FORMATS
from .exceptions import UnsupportedFormatError

OutputFormat = Literal["wav", "mp3", "flac", "ogg", "m4a"]


@dataclass(frozen=True, slots=True)
class MediaStream:
    index: int
    codec_type: str
    codec_name: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    channel_layout: str | None = None


@dataclass(frozen=True, slots=True)
class MediaInfo:
    path: Path
    size_bytes: int
    duration_seconds: float | None
    format_name: str | None
    streams: tuple[MediaStream, ...] = field(default_factory=tuple)

    @property
    def audio_streams(self) -> tuple[MediaStream, ...]:
        return tuple(stream for stream in self.streams if stream.codec_type == "audio")


@dataclass(frozen=True, slots=True)
class ProgressUpdate:
    state: str
    out_time_seconds: float | None = None
    percent: float | None = None
    speed: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractionOptions:
    output_format: OutputFormat = "wav"
    sample_rate: int | None = DEFAULT_SAMPLE_RATE
    channels: int | None = DEFAULT_CHANNELS
    timeout: float = 300.0
    overwrite: bool = False
    max_file_size_bytes: int | None = None
    max_duration_seconds: float | None = None
    audio_stream_index: int = 0
    probe_timeout: float = 15.0
    terminate_grace_period: float = 2.0

    def __post_init__(self) -> None:
        if self.output_format not in SUPPORTED_FORMATS:
            raise UnsupportedFormatError(
                f"Unsupported format: {self.output_format}. "
                f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        if self.sample_rate is not None and self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive or None")
        if self.channels is not None and self.channels <= 0:
            raise ValueError("channels must be positive or None")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if self.probe_timeout <= 0:
            raise ValueError("probe_timeout must be greater than zero")
        if self.terminate_grace_period < 0:
            raise ValueError("terminate_grace_period cannot be negative")
        if self.max_file_size_bytes is not None and self.max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be positive or None")
        if self.max_duration_seconds is not None and self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be positive or None")
        if self.audio_stream_index < 0:
            raise ValueError("audio_stream_index cannot be negative")


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    source: Path
    path: Path
    format: str
    bytes_written: int
    elapsed_seconds: float
    media_info: MediaInfo
