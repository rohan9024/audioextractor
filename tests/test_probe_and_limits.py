from __future__ import annotations

from pathlib import Path

import pytest

from audioextract import MediaLimitError, NoAudioStreamError, extract_audio, probe_media


def test_probe_finds_audio(sample_video: Path) -> None:
    info = probe_media(sample_video)
    assert info.duration_seconds is not None
    assert len(info.audio_streams) == 1
    assert info.size_bytes > 0


def test_rejects_duration_limit(sample_video: Path, tmp_path: Path) -> None:
    with pytest.raises(MediaLimitError):
        extract_audio(
            sample_video,
            tmp_path / "out.wav",
            max_duration_seconds=0.5,
        )


def test_rejects_file_size_limit(sample_video: Path, tmp_path: Path) -> None:
    with pytest.raises(MediaLimitError):
        extract_audio(
            sample_video,
            tmp_path / "out.wav",
            max_file_size_bytes=10,
        )


def test_rejects_video_without_audio(silent_video: Path, tmp_path: Path) -> None:
    with pytest.raises(NoAudioStreamError):
        extract_audio(silent_video, tmp_path / "out.wav")
