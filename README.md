# audioextract

Production-safe audio extraction for Python media and AI pipelines.

`audioextract` is intentionally small: it runs FFmpeg safely around local media files while handling the production details that are easy to get wrong in application code.

## What it adds over a raw FFmpeg subprocess

- sync and true async APIs
- async cancellation cleanup
- process-tree termination on timeout/cancellation
- ffprobe preflight validation
- file-size and duration safety limits
- bounded concurrency through `AudioExtractor`
- atomic partial-file output and failed-job cleanup
- bounded stderr capture instead of buffering unlimited FFmpeg output
- progress callbacks
- structured media metadata, results, and exceptions
- Windows, macOS, and Linux support target

It does **not** transcribe, summarize, call an LLM, download YouTube videos, or replace FFmpeg.

## Requirements

Python 3.10+ and FFmpeg/ffprobe installed on the host.

```bash
ffmpeg -version
ffprobe -version
```

## Install for local development

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
```

## Basic usage

```python
from audioextract import extract_audio

result = extract_audio(
    "meeting.mp4",
    output_format="wav",
    max_duration_seconds=7200,
)

print(result.path)
print(result.bytes_written)
```

## Async / FastAPI-friendly usage

```python
from audioextract import extract_audio_async

result = await extract_audio_async(
    "meeting.mp4",
    output_format="wav",
    timeout=600,
)
```

If the surrounding task is cancelled, `audioextract` terminates the FFmpeg process tree, waits for it to exit, and removes its partial output.

## Bounded concurrency

```python
import asyncio
from audioextract import AudioExtractor, ExtractionOptions

extractor = AudioExtractor(
    max_concurrency=3,
    options=ExtractionOptions(
        output_format="wav",
        max_file_size_bytes=2 * 1024**3,
        max_duration_seconds=2 * 60 * 60,
    ),
)

async def main():
    results = await asyncio.gather(
        extractor.extract_async("one.mp4"),
        extractor.extract_async("two.mp4"),
        extractor.extract_async("three.mp4"),
        extractor.extract_async("four.mp4"),
    )
    print([r.path for r in results])

asyncio.run(main())
```

## Progress

```python
from audioextract import ProgressUpdate, extract_audio

def on_progress(update: ProgressUpdate):
    if update.percent is not None:
        print(f"{update.percent:.1f}%")

extract_audio("meeting.mp4", progress=on_progress)
```

Async progress callbacks may be normal functions or async functions.

## Preserve the original sample rate/channels

The defaults are 16 kHz mono because they are convenient for speech pipelines. Set either to `None` to avoid forcing that property:

```python
extract_audio(
    "music-video.mp4",
    sample_rate=None,
    channels=None,
    output_format="flac",
)
```

## CLI

```bash
audioextract input.mp4 -o output.wav --max-duration 7200 --overwrite
```

## Safety behavior

Before FFmpeg starts, the package uses ffprobe to inspect the input. It can reject files that exceed configured limits or contain no audio stream.

FFmpeg writes to a hidden temporary file in the destination directory. Only after a successful extraction is that file atomically moved to the final destination. Failed, timed-out, or cancelled jobs clean up the temporary file.

No command is executed through a shell; file paths are passed as subprocess arguments.

## Tests

```bash
pytest -v
```

The integration suite generates its own small media fixtures with FFmpeg.

## Benchmarks

```bash
python benchmarks/benchmark_single.py
python benchmarks/benchmark_concurrency.py
```

Do not claim performance wins without running benchmarks on the target environment. This library's main value proposition is predictable lifecycle management and a small API, not magically making FFmpeg faster.

## Scope

Version 0.2 processes **local files only**. URL downloading, cloud storage, transcription providers, and LLM integrations are intentionally outside the core package.

## License

MIT
