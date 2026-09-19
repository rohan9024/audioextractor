from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from audioextract import OutputExistsError, ProgressUpdate, extract_audio


def test_extract_wav(sample_video: Path, tmp_path: Path) -> None:
    result = extract_audio(sample_video, tmp_path / "out.wav")
    assert result.path.exists()
    assert result.path.suffix == ".wav"
    assert result.bytes_written > 0
    assert result.media_info.audio_streams


def test_extract_mp3(sample_video: Path, tmp_path: Path) -> None:
    result = extract_audio(
        sample_video,
        tmp_path / "out.mp3",
        output_format="mp3",
    )
    assert result.path.exists()
    assert result.path.suffix == ".mp3"


def test_output_exists_requires_overwrite(sample_video: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.wav"
    extract_audio(sample_video, out)
    with pytest.raises(OutputExistsError):
        extract_audio(sample_video, out)
    extract_audio(sample_video, out, overwrite=True)


def test_unicode_and_spaces_in_path(sample_video: Path, tmp_path: Path) -> None:
    copied = tmp_path / "média test ünicode.mp4"
    shutil.copy2(sample_video, copied)
    result = extract_audio(copied, tmp_path / "áudio result.wav")
    assert result.path.exists()


def test_progress_callback_receives_updates(sample_video: Path, tmp_path: Path) -> None:
    updates: list[ProgressUpdate] = []
    extract_audio(sample_video, tmp_path / "out.wav", progress=updates.append)
    assert updates
    assert updates[-1].state == "end"
    assert updates[-1].percent == 100.0
