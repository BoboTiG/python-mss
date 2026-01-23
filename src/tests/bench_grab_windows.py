"""Quick benchmark for Windows grab performance.

This script measures the performance of the Windows GDI grab implementation
using CreateDIBSection.

Run with: python -m tests.bench_grab_windows
         python -m tests.bench_grab_windows timing
         python -m tests.bench_grab_windows raw
"""

from __future__ import annotations

import sys
from time import perf_counter

import mss

ITERATIONS = 500
WARMUP_ITERATIONS = 10


def benchmark_grab() -> tuple[float, float]:
    """Benchmark the grab operation on the primary monitor.

    Returns (avg_ms, fps) for comparison.
    """
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

        return avg_ms, fps


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


def benchmark_raw_bitblt() -> None:
    """Benchmark raw BitBlt to isolate GDI performance from Python overhead."""
    if sys.platform != "win32":
        print("Raw BitBlt benchmark is only available on Windows.")
        return

    import ctypes  # noqa: PLC0415
    from ctypes.wintypes import BOOL, DWORD, HDC, INT  # noqa: PLC0415

    import mss.windows  # noqa: PLC0415

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    # Get function references (names match Windows API)
    bitblt = gdi32.BitBlt
    bitblt.argtypes = [HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD]
    bitblt.restype = BOOL

    gdiflush = gdi32.GdiFlush
    gdiflush.argtypes = []
    gdiflush.restype = BOOL

    srccopy = 0x00CC0020
    captureblt = 0x40000000

    with mss.mss() as sct:
        assert isinstance(sct, mss.windows.MSS)
        monitor = sct.monitors[1]
        width, height = monitor["width"], monitor["height"]
        left, top = monitor["left"], monitor["top"]

        # Force region setup
        sct.grab(monitor)

        srcdc = sct._srcdc
        memdc = sct._memdc

        print(f"Raw BitBlt benchmark ({width}x{height})")
        print("=" * 50)

        # Test with CAPTUREBLT
        start = perf_counter()
        for _ in range(ITERATIONS):
            bitblt(memdc, 0, 0, width, height, srcdc, left, top, srccopy | captureblt)
            gdiflush()
        elapsed = perf_counter() - start
        print(f"With CAPTUREBLT:    {elapsed / ITERATIONS * 1000:.2f}ms ({ITERATIONS / elapsed:.1f} FPS)")

        # Test without CAPTUREBLT
        start = perf_counter()
        for _ in range(ITERATIONS):
            bitblt(memdc, 0, 0, width, height, srcdc, left, top, srccopy)
            gdiflush()
        elapsed = perf_counter() - start
        print(f"Without CAPTUREBLT: {elapsed / ITERATIONS * 1000:.2f}ms ({ITERATIONS / elapsed:.1f} FPS)")


def analyze_frame_timing() -> None:
    """Analyze individual frame timing to detect VSync/DWM patterns."""
    num_samples = 200

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        width, height = monitor["width"], monitor["height"]

        print("Frame timing analysis")
        print(f"Region: {width}x{height}")
        print(f"Samples: {num_samples}")
        print("=" * 50)

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            sct.grab(monitor)

        # Collect individual frame times
        times: list[float] = []
        prev = perf_counter()
        for _ in range(num_samples):
            sct.grab(monitor)
            now = perf_counter()
            times.append((now - prev) * 1000)  # Convert to ms
            prev = now

        # Analyze the distribution
        times.sort()
        min_t = times[0]
        max_t = times[-1]
        avg_t = sum(times) / len(times)
        median_t = times[len(times) // 2]

        # Calculate percentiles
        p5 = times[int(len(times) * 0.05)]
        p95 = times[int(len(times) * 0.95)]

        print("\nTiming distribution:")
        print(f"  Min:    {min_t:.2f}ms")
        print(f"  5th %:  {p5:.2f}ms")
        print(f"  Median: {median_t:.2f}ms")
        print(f"  Avg:    {avg_t:.2f}ms")
        print(f"  95th %: {p95:.2f}ms")
        print(f"  Max:    {max_t:.2f}ms")

        # Check for VSync patterns
        print("\nVSync pattern analysis:")
        print("  60 Hz (16.67ms): ", end="")
        near_60hz = sum(1 for t in times if 15 < t < 18)
        print(f"{near_60hz}/{num_samples} samples ({near_60hz / num_samples * 100:.0f}%)")

        print("  30 Hz (33.33ms): ", end="")
        near_30hz = sum(1 for t in times if 31 < t < 36)
        print(f"{near_30hz}/{num_samples} samples ({near_30hz / num_samples * 100:.0f}%)")

        print("  < 10ms (fast):   ", end="")
        fast = sum(1 for t in times if t < 10)
        print(f"{fast}/{num_samples} samples ({fast / num_samples * 100:.0f}%)")

        # Histogram buckets
        print("\nHistogram (ms):")
        buckets = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 100]
        for i in range(len(buckets) - 1):
            lo, hi = buckets[i], buckets[i + 1]
            count = sum(1 for t in times if lo <= t < hi)
            bar = "#" * (count * 40 // num_samples)
            print(f"  {lo:3d}-{hi:3d}: {bar} ({count})")
        # Overflow bucket
        count = sum(1 for t in times if t >= buckets[-1])
        if count > 0:
            bar = "#" * (count * 40 // num_samples)
            print(f"  {buckets[-1]:3d}+  : {bar} ({count})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "raw":
            benchmark_raw_bitblt()
            sys.exit(0)
        if arg == "timing":
            analyze_frame_timing()
            sys.exit(0)

    benchmark_grab()
    benchmark_grab_varying_sizes()
