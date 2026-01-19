"""Quick benchmark for Windows grab performance.

This script is designed to measure the performance of the Windows grab
implementation, particularly useful for comparing GetDIBits vs CreateDIBSection
approaches.

Run with: python -m tests.bench_grab_windows
"""

from __future__ import annotations

import sys
from time import perf_counter

import mss

ITERATIONS = 500
WARMUP_ITERATIONS = 10


def benchmark_grab() -> None:
    """Benchmark the grab operation on the primary monitor."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Primary monitor
        width, height = monitor["width"], monitor["height"]

        print(f"Platform: {sys.platform}")
        print(f"Region: {width}x{height}")
        print(f"Iterations: {ITERATIONS}")
        print()

        # Warmup - let any JIT/caching settle
        for _ in range(WARMUP_ITERATIONS):
            sct.grab(monitor)

        # Benchmark
        start = perf_counter()
        for _ in range(ITERATIONS):
            sct.grab(monitor)
        elapsed = perf_counter() - start

        avg_ms = elapsed / ITERATIONS * 1000
        fps = ITERATIONS / elapsed

        print(f"Total time: {elapsed:.3f}s")
        print(f"Avg per grab: {avg_ms:.2f}ms")
        print(f"FPS: {fps:.1f}")


def benchmark_grab_varying_sizes() -> None:
    """Benchmark grab at different region sizes to see scaling behavior."""
    sizes = [
        (100, 100),
        (640, 480),
        (1280, 720),
        (1920, 1080),
    ]

    print("\nVarying size benchmark:")
    print("-" * 50)

    with mss.mss() as sct:
        for width, height in sizes:
            monitor = {"top": 0, "left": 0, "width": width, "height": height}

            # Warmup
            for _ in range(WARMUP_ITERATIONS):
                sct.grab(monitor)

            # Benchmark
            start = perf_counter()
            for _ in range(ITERATIONS):
                sct.grab(monitor)
            elapsed = perf_counter() - start

            avg_ms = elapsed / ITERATIONS * 1000
            fps = ITERATIONS / elapsed
            print(f"  {width}x{height}: {avg_ms:.2f}ms ({fps:.1f} FPS)")


if __name__ == "__main__":
    benchmark_grab()
    benchmark_grab_varying_sizes()
