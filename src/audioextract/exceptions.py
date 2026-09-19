"""Exception hierarchy for audioextract."""
from __future__ import annotations


class AudioExtractError(Exception):
    """Base exception for all package errors."""


class FFmpegNotFoundError(AudioExtractError):
    """Raised when FFmpeg cannot be located."""


class FFprobeNotFoundError(AudioExtractError):
    """Raised when ffprobe cannot be located."""


class InvalidInputError(AudioExtractError):
    """Raised when the source media is invalid or inaccessible."""


class UnsupportedFormatError(AudioExtractError):
    """Raised when an unsupported output format is requested."""


class OutputExistsError(AudioExtractError):
    """Raised when the destination already exists and overwrite is disabled."""


class NoAudioStreamError(AudioExtractError):
    """Raised when the input media has no audio stream."""


class MediaLimitError(AudioExtractError):
    """Raised when an input exceeds a configured safety limit."""


class ExtractionTimeoutError(AudioExtractError):
    """Raised when FFmpeg exceeds the configured timeout."""


class FFmpegExecutionError(AudioExtractError):
    """Raised when FFmpeg exits unsuccessfully."""

    def __init__(self, returncode: int, stderr: str) -> None:
        self.returncode = returncode
        self.stderr = stderr
        message = f"FFmpeg failed with exit code {returncode}."
        if stderr:
            message += f"\n{stderr}"
        super().__init__(message)


class ProbeError(AudioExtractError):
    """Raised when ffprobe cannot inspect the source media."""
