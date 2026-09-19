from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from audioextract import AudioExtractor, ExtractionOptions, extract_audio_async


@pytest.mark.asyncio
async def test_async_extract(sample_video: Path, tmp_path: Path) -> None:
    result = await extract_audio_async(sample_video, tmp_path / "async.wav")
    assert result.path.exists()
    assert result.bytes_written > 0


@pytest.mark.asyncio
async def test_async_progress_callback_can_be_async(sample_video: Path, tmp_path: Path) -> None:
    states: list[str] = []

    async def progress(update):
        await asyncio.sleep(0)
        states.append(update.state)

    await extract_audio_async(sample_video, tmp_path / "progress.wav", progress=progress)
    assert "end" in states


@pytest.mark.asyncio
async def test_bounded_concurrency_api(sample_video: Path, tmp_path: Path) -> None:
    extractor = AudioExtractor(
        max_concurrency=2,
        options=ExtractionOptions(overwrite=True),
    )
    results = await asyncio.gather(
        extractor.extract_async(sample_video, tmp_path / "one.wav"),
        extractor.extract_async(sample_video, tmp_path / "two.wav"),
        extractor.extract_async(sample_video, tmp_path / "three.wav"),
    )
    assert all(result.path.exists() for result in results)
