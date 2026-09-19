from __future__ import annotations

import pytest

from audioextract import ExtractionOptions, UnsupportedFormatError


def test_default_options_are_speech_friendly() -> None:
    options = ExtractionOptions()
    assert options.output_format == "wav"
    assert options.sample_rate == 16000
    assert options.channels == 1


def test_rejects_invalid_format() -> None:
    with pytest.raises(UnsupportedFormatError):
        ExtractionOptions(output_format="xyz")  # type: ignore[arg-type]


def test_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        ExtractionOptions(max_duration_seconds=0)
    with pytest.raises(ValueError):
        ExtractionOptions(max_file_size_bytes=-1)
