"""Production-safe audio extraction for Python media and AI pipelines."""
from __future__ import annotations

from .exceptions import (
    AudioExtractError,
    ExtractionTimeoutError,
    FFmpegExecutionError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    InvalidInputError,
    MediaLimitError,
    NoAudioStreamError,
    OutputExistsError,
    ProbeError,
    UnsupportedFormatError,
)
from .extractor import AudioExtractor, extract_audio, extract_audio_async
from .models import (
    ExtractionOptions,
    ExtractionResult,
    MediaInfo,
    MediaStream,
    ProgressUpdate,
)
from .probing import probe_media

__version__ = "0.2.1"

__all__ = [
    "AudioExtractor",
    "extract_audio",
    "extract_audio_async",
    "probe_media",
    "ExtractionOptions",
    "ExtractionResult",
    "MediaInfo",
    "MediaStream",
    "ProgressUpdate",
    "AudioExtractError",
    "ExtractionTimeoutError",
    "FFmpegExecutionError",
    "FFmpegNotFoundError",
    "FFprobeNotFoundError",
    "InvalidInputError",
    "MediaLimitError",
    "NoAudioStreamError",
    "OutputExistsError",
    "ProbeError",
    "UnsupportedFormatError",
]
