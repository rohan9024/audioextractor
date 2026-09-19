from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from audioextract import AudioExtractor, ExtractionOptions


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()

    extractor = AudioExtractor(
        max_concurrency=args.concurrency,
        options=ExtractionOptions(overwrite=True),
    )

    started = time.perf_counter()
    results = await asyncio.gather(
        *[
            extractor.extract_async(
                args.source,
                Path(f"benchmark-{index}.wav"),
            )
            for index in range(args.jobs)
        ]
    )
    elapsed = time.perf_counter() - started

    print(f"jobs: {len(results)}")
    print(f"max_concurrency: {args.concurrency}")
    print(f"elapsed_seconds: {elapsed:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
