"""Command-line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exceptions import AudioExtractError
from .extractor import extract_audio
from .models import ProgressUpdate


def _progress(update: ProgressUpdate) -> None:
    if update.percent is not None:
        print(
            f"\r{update.percent:6.2f}%  speed={update.speed or '?'}",
            end="",
            flush=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audioextract",
        description="Safely extract audio from local media files using FFmpeg.",
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument(
    "-f",
    "--format",
    default="wav",
    choices=["wav", "mp3", "flac", "ogg", "m4a"],
    )
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-duration", type=float)
    parser.add_argument("--max-size", type=int, help="Maximum input size in bytes")
    parser.add_argument("--audio-stream", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-progress", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = extract_audio(
            args.source,
            args.output,
            output_format=args.format,
            sample_rate=args.sample_rate,
            channels=args.channels,
            timeout=args.timeout,
            overwrite=args.overwrite,
            max_file_size_bytes=args.max_size,
            max_duration_seconds=args.max_duration,
            audio_stream_index=args.audio_stream,
            progress=None if args.no_progress else _progress,
        )
    except AudioExtractError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1

    if not args.no_progress:
        print()
    print(
        f"saved {result.path} ({result.bytes_written} bytes, "
        f"{result.elapsed_seconds:.2f}s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
