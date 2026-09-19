from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import psutil

from audioextract import extract_audio


def tree_rss_bytes() -> int:
    process = psutil.Process()
    total = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("benchmark.wav"))
    args = parser.parse_args()

    stop = threading.Event()
    peak = 0

    def sampler() -> None:
        nonlocal peak
        while not stop.is_set():
            peak = max(peak, tree_rss_bytes())
            time.sleep(0.05)

    thread = threading.Thread(target=sampler, daemon=True)
    thread.start()
    started = time.perf_counter()
    try:
        result = extract_audio(args.source, args.output, overwrite=True)
    finally:
        stop.set()
        thread.join()

    elapsed = time.perf_counter() - started
    print(f"source: {args.source}")
    print(f"output: {result.path}")
    print(f"elapsed_seconds: {elapsed:.3f}")
    print(f"peak_process_tree_rss_mb: {peak / 1024**2:.2f}")
