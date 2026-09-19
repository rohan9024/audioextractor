from __future__ import annotations

import asyncio
import sys

import pytest

from audioextract.exceptions import ExtractionTimeoutError
from audioextract.process import run_ffmpeg_async, run_ffmpeg_sync


def test_sync_timeout_terminates_process() -> None:
    with pytest.raises(ExtractionTimeoutError):
        run_ffmpeg_sync(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout=0.05,
            total_duration=None,
            progress=None,
            terminate_grace_period=0.05,
        )


@pytest.mark.asyncio
async def test_async_timeout_terminates_process() -> None:
    with pytest.raises(ExtractionTimeoutError):
        await run_ffmpeg_async(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            timeout=0.05,
            total_duration=None,
            progress=None,
            terminate_grace_period=0.05,
        )
