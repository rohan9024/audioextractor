"""High-level extraction APIs."""
from __future__ import annotations

import asyncio
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ._utils import (
    atomic_replace,
    ensure_parent,
    resolve_ffmpeg,
    safe_unlink,
    temporary_output_path,
    validate_source,
)
from .constants import CODECS, DEFAULT_CHANNELS, DEFAULT_SAMPLE_RATE
from .exceptions import AudioExtractError, OutputExistsError
from .limits import enforce_limits
from .models import ExtractionOptions, ExtractionResult, MediaInfo, ProgressUpdate
from .probing import probe_media
from .process import AsyncProgressCallback, ProgressCallback, run_ffmpeg_async, run_ffmpeg_sync


@dataclass(frozen=True, slots=True)
class _PreparedJob:
    source: Path
    target: Path
    temporary: Path
    media: MediaInfo
    command: list[str]


def _target_path(source: Path, output_path: str | Path | None, output_format: str) -> Path:
    if output_path is None:
        target = source.with_suffix(f".{output_format}")
    else:
        target = Path(output_path).expanduser().resolve()

    if target == source:
        raise AudioExtractError(
            "Input and output resolve to the same path. Choose a different output path."
        )
    return target


def _build_ffmpeg_command(
    *,
    ffmpeg: str,
    source: Path,
    temporary: Path,
    options: ExtractionOptions,
) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-i",
        str(source),
        "-map",
        f"0:a:{options.audio_stream_index}",
        "-vn",
        "-sn",
        "-dn",
        "-c:a",
        CODECS[options.output_format],
    ]

    if options.sample_rate is not None:
        command += ["-ar", str(options.sample_rate)]
    if options.channels is not None:
        command += ["-ac", str(options.channels)]

    command += [
        "-progress",
        "pipe:1",
        "-nostats",
        "-y",
        str(temporary),
    ]
    return command


def _prepare_job(
    source: str | Path,
    output_path: str | Path | None,
    *,
    options: ExtractionOptions,
    ffmpeg_path: str | Path | None,
    ffprobe_path: str | Path | None,
) -> _PreparedJob:
    source_path = validate_source(source)
    target = _target_path(source_path, output_path, options.output_format)
    ensure_parent(target)

    if target.exists() and not options.overwrite:
        raise OutputExistsError(
            f"Output already exists: {target}. Pass overwrite=True to replace it."
        )

    media = probe_media(
        source_path,
        ffprobe_path=ffprobe_path,
        timeout=options.probe_timeout,
    )
    enforce_limits(media, options)

    ffmpeg = resolve_ffmpeg(ffmpeg_path)
    temporary = temporary_output_path(target)
    command = _build_ffmpeg_command(
        ffmpeg=ffmpeg,
        source=source_path,
        temporary=temporary,
        options=options,
    )
    return _PreparedJob(source_path, target, temporary, media, command)


def _finalize(job: _PreparedJob, options: ExtractionOptions, elapsed: float) -> ExtractionResult:
    if not job.temporary.exists() or job.temporary.stat().st_size <= 0:
        raise AudioExtractError(
            f"FFmpeg exited successfully but produced no usable output for {job.source.name}."
        )

    if job.target.exists() and not options.overwrite:
        raise OutputExistsError(
            f"Output appeared while extraction was running: {job.target}"
        )

    atomic_replace(job.temporary, job.target)
    return ExtractionResult(
        source=job.source,
        path=job.target,
        format=options.output_format,
        bytes_written=job.target.stat().st_size,
        elapsed_seconds=elapsed,
        media_info=job.media,
    )


def extract_audio(
    source: str | Path,
    output_path: str | Path | None = None,
    *,
    output_format: str = "wav",
    sample_rate: int | None = DEFAULT_SAMPLE_RATE,
    channels: int | None = DEFAULT_CHANNELS,
    timeout: float = 300.0,
    overwrite: bool = False,
    max_file_size_bytes: int | None = None,
    max_duration_seconds: float | None = None,
    audio_stream_index: int = 0,
    ffmpeg_path: str | Path | None = None,
    ffprobe_path: str | Path | None = None,
    progress: ProgressCallback | None = None,
) -> ExtractionResult:
    """Extract audio from a local media file with preflight checks and safe cleanup."""
    options = ExtractionOptions(
        output_format=output_format,  # type: ignore[arg-type]
        sample_rate=sample_rate,
        channels=channels,
        timeout=timeout,
        overwrite=overwrite,
        max_file_size_bytes=max_file_size_bytes,
        max_duration_seconds=max_duration_seconds,
        audio_stream_index=audio_stream_index,
    )
    job = _prepare_job(
        source,
        output_path,
        options=options,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )

    started = time.monotonic()
    try:
        run_ffmpeg_sync(
            job.command,
            timeout=options.timeout,
            total_duration=job.media.duration_seconds,
            progress=progress,
            terminate_grace_period=options.terminate_grace_period,
        )
        return _finalize(job, options, time.monotonic() - started)
    except BaseException:
        safe_unlink(job.temporary)
        raise


async def extract_audio_async(
    source: str | Path,
    output_path: str | Path | None = None,
    *,
    output_format: str = "wav",
    sample_rate: int | None = DEFAULT_SAMPLE_RATE,
    channels: int | None = DEFAULT_CHANNELS,
    timeout: float = 300.0,
    overwrite: bool = False,
    max_file_size_bytes: int | None = None,
    max_duration_seconds: float | None = None,
    audio_stream_index: int = 0,
    ffmpeg_path: str | Path | None = None,
    ffprobe_path: str | Path | None = None,
    progress: AsyncProgressCallback | None = None,
) -> ExtractionResult:
    """Async extraction API that is safe to cancel from FastAPI/task workers."""
    options = ExtractionOptions(
        output_format=output_format,  # type: ignore[arg-type]
        sample_rate=sample_rate,
        channels=channels,
        timeout=timeout,
        overwrite=overwrite,
        max_file_size_bytes=max_file_size_bytes,
        max_duration_seconds=max_duration_seconds,
        audio_stream_index=audio_stream_index,
    )

    job = await asyncio.to_thread(
        _prepare_job,
        source,
        output_path,
        options=options,
        ffmpeg_path=ffmpeg_path,
        ffprobe_path=ffprobe_path,
    )

    started = time.monotonic()
    try:
        await run_ffmpeg_async(
            job.command,
            timeout=options.timeout,
            total_duration=job.media.duration_seconds,
            progress=progress,
            terminate_grace_period=options.terminate_grace_period,
        )
        return await asyncio.to_thread(
            _finalize, job, options, time.monotonic() - started
        )
    except BaseException:
        await asyncio.to_thread(safe_unlink, job.temporary)
        raise


class AudioExtractor:
    """Reusable extractor with bounded sync and async concurrency."""

    def __init__(
        self,
        *,
        max_concurrency: int = 4,
        options: ExtractionOptions | None = None,
        ffmpeg_path: str | Path | None = None,
        ffprobe_path: str | Path | None = None,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than zero")
        self.options = options or ExtractionOptions()
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._sync_semaphore = threading.BoundedSemaphore(max_concurrency)
        self._async_semaphore = asyncio.Semaphore(max_concurrency)

    def extract(
        self,
        source: str | Path,
        output_path: str | Path | None = None,
        *,
        progress: ProgressCallback | None = None,
    ) -> ExtractionResult:
        with self._sync_semaphore:
            job = _prepare_job(
                source,
                output_path,
                options=self.options,
                ffmpeg_path=self.ffmpeg_path,
                ffprobe_path=self.ffprobe_path,
            )
            started = time.monotonic()
            try:
                run_ffmpeg_sync(
                    job.command,
                    timeout=self.options.timeout,
                    total_duration=job.media.duration_seconds,
                    progress=progress,
                    terminate_grace_period=self.options.terminate_grace_period,
                )
                return _finalize(job, self.options, time.monotonic() - started)
            except BaseException:
                safe_unlink(job.temporary)
                raise

    async def extract_async(
        self,
        source: str | Path,
        output_path: str | Path | None = None,
        *,
        progress: AsyncProgressCallback | None = None,
    ) -> ExtractionResult:
        async with self._async_semaphore:
            job = await asyncio.to_thread(
                _prepare_job,
                source,
                output_path,
                options=self.options,
                ffmpeg_path=self.ffmpeg_path,
                ffprobe_path=self.ffprobe_path,
            )
            started = time.monotonic()
            try:
                await run_ffmpeg_async(
                    job.command,
                    timeout=self.options.timeout,
                    total_duration=job.media.duration_seconds,
                    progress=progress,
                    terminate_grace_period=self.options.terminate_grace_period,
                )
                return await asyncio.to_thread(
                    _finalize, job, self.options, time.monotonic() - started
                )
            except BaseException:
                await asyncio.to_thread(safe_unlink, job.temporary)
                raise
