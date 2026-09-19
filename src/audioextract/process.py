"""Cross-platform FFmpeg process supervision."""
from __future__ import annotations

import asyncio
import inspect
import os
import subprocess
import threading
from collections import deque
from collections.abc import Awaitable, Callable
from typing import IO, Any

import psutil

from .exceptions import AudioExtractError, ExtractionTimeoutError, FFmpegExecutionError
from .models import ProgressUpdate
from .progress import progress_from_record

ProgressCallback = Callable[[ProgressUpdate], Any]
AsyncProgressCallback = Callable[[ProgressUpdate], Any | Awaitable[Any]]


def _spawn_kwargs() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def terminate_process_tree(pid: int, grace_period: float = 2.0) -> None:
    """Terminate a process and all descendants, then force-kill survivors."""
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return

    processes = parent.children(recursive=True)
    processes.append(parent)

    for process in reversed(processes):
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass

    _, alive = psutil.wait_procs(processes, timeout=grace_period)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass
    if alive:
        psutil.wait_procs(alive, timeout=max(1.0, grace_period))


def _bounded_stderr_reader(stream: IO[str], lines: deque[str]) -> None:
    for line in iter(stream.readline, ""):
        clean = line.rstrip()
        if clean:
            lines.append(clean)


def _progress_reader(
    stream: IO[str],
    *,
    total_duration: float | None,
    callback: ProgressCallback | None,
    callback_error: list[BaseException],
    process_pid: int,
    grace_period: float,
) -> None:
    record: dict[str, str] = {}
    for line in iter(stream.readline, ""):
        clean = line.strip()
        if not clean or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        record[key] = value
        if key != "progress":
            continue

        if callback is not None:
            try:
                callback(progress_from_record(record, total_duration))
            except BaseException as exc:  # user callback failure must stop the job
                callback_error.append(exc)
                terminate_process_tree(process_pid, grace_period)
                return
        record = {}


def run_ffmpeg_sync(
    cmd: list[str],
    *,
    timeout: float,
    total_duration: float | None,
    progress: ProgressCallback | None,
    terminate_grace_period: float,
) -> None:
    """Run FFmpeg without allowing pipe buffers or orphaned children to accumulate."""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **_spawn_kwargs(),
    )
    assert process.stdout is not None
    assert process.stderr is not None

    stderr_lines: deque[str] = deque(maxlen=80)
    callback_error: list[BaseException] = []

    stdout_thread = threading.Thread(
        target=_progress_reader,
        kwargs={
            "stream": process.stdout,
            "total_duration": total_duration,
            "callback": progress,
            "callback_error": callback_error,
            "process_pid": process.pid,
            "grace_period": terminate_grace_period,
        },
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_bounded_stderr_reader,
        args=(process.stderr, stderr_lines),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        try:
            returncode = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            terminate_process_tree(process.pid, terminate_grace_period)
            try:
                process.wait(timeout=max(1.0, terminate_grace_period + 1.0))
            except subprocess.TimeoutExpired:
                pass
            raise ExtractionTimeoutError(
                f"FFmpeg exceeded the {timeout:.2f}s timeout."
            ) from exc
    except KeyboardInterrupt:
        terminate_process_tree(process.pid, terminate_grace_period)
        raise
    finally:
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)
        process.stdout.close()
        process.stderr.close()

    if callback_error:
        raise AudioExtractError("Progress callback raised an exception") from callback_error[0]

    if returncode != 0:
        raise FFmpegExecutionError(returncode, "\n".join(stderr_lines))


async def _read_async_stderr(stream: asyncio.StreamReader, lines: deque[str]) -> None:
    while True:
        raw = await stream.readline()
        if not raw:
            return
        clean = raw.decode("utf-8", errors="replace").rstrip()
        if clean:
            lines.append(clean)


async def _read_async_progress(
    stream: asyncio.StreamReader,
    *,
    total_duration: float | None,
    callback: AsyncProgressCallback | None,
) -> None:
    record: dict[str, str] = {}
    while True:
        raw = await stream.readline()
        if not raw:
            return
        clean = raw.decode("utf-8", errors="replace").strip()
        if not clean or "=" not in clean:
            continue
        key, value = clean.split("=", 1)
        record[key] = value
        if key != "progress":
            continue

        if callback is not None:
            result = callback(progress_from_record(record, total_duration))
            if inspect.isawaitable(result):
                await result
        record = {}


async def run_ffmpeg_async(
    cmd: list[str],
    *,
    timeout: float,
    total_duration: float | None,
    progress: AsyncProgressCallback | None,
    terminate_grace_period: float,
) -> None:
    """Run FFmpeg asynchronously and guarantee cleanup on timeout/cancellation."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **_spawn_kwargs(),
    )
    assert process.stdout is not None
    assert process.stderr is not None

    stderr_lines: deque[str] = deque(maxlen=80)
    stdout_task = asyncio.create_task(
        _read_async_progress(
            process.stdout,
            total_duration=total_duration,
            callback=progress,
        )
    )
    stderr_task = asyncio.create_task(_read_async_stderr(process.stderr, stderr_lines))

    # Keep one stable wait task for the process lifetime.  In Python 3.10,
    # asyncio.wait_for() cancels the awaitable it wraps on timeout.  Cancelling
    # Process.wait() is particularly awkward on Windows' Proactor event loop,
    # so shield the wait task and terminate the process tree ourselves.
    wait_task = asyncio.create_task(process.wait())

    async def settle_after_termination() -> None:
        """Wait briefly for the killed process transport to settle."""
        try:
            await asyncio.wait_for(
                asyncio.shield(wait_task),
                timeout=max(1.0, terminate_grace_period + 1.0),
            )
        except asyncio.TimeoutError:
            # The OS process has already been terminated by terminate_process_tree.
            # Do not leave an asyncio task pending if the platform transport is slow
            # to report process exit.
            wait_task.cancel()
            await asyncio.gather(wait_task, return_exceptions=True)

    try:
        try:
            returncode = await asyncio.wait_for(
                asyncio.shield(wait_task), timeout=timeout
            )
        except asyncio.TimeoutError as exc:
            await asyncio.to_thread(
                terminate_process_tree, process.pid, terminate_grace_period
            )
            await settle_after_termination()
            raise ExtractionTimeoutError(
                f"FFmpeg exceeded the {timeout:.2f}s timeout."
            ) from exc
    except asyncio.CancelledError:
        await asyncio.to_thread(
            terminate_process_tree, process.pid, terminate_grace_period
        )
        await settle_after_termination()
        raise
    except BaseException:
        if process.returncode is None:
            await asyncio.to_thread(
                terminate_process_tree, process.pid, terminate_grace_period
            )
            await settle_after_termination()
        raise
    finally:
        reader_results = await asyncio.gather(
            stdout_task, stderr_task, return_exceptions=True
        )

    for result in reader_results:
        if isinstance(result, BaseException):
            raise AudioExtractError("A progress/output reader failed") from result

    if returncode != 0:
        raise FFmpegExecutionError(returncode, "\n".join(stderr_lines))
