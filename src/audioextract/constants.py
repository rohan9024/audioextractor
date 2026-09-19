"""Package constants."""
from __future__ import annotations

SUPPORTED_FORMATS = ("wav", "mp3", "flac", "ogg", "m4a")
CODECS = {
    "wav": "pcm_s16le",
    "mp3": "libmp3lame",
    "flac": "flac",
    "ogg": "libvorbis",
    "m4a": "aac",
}
DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_CHANNELS = 1
