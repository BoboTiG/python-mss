# Python-MSS 10.2.0

This is **version 10.2.0 of Python-MSS**, the ultra-fast cross-platform multiple screenshots module.

This release improves **performance, reliability, and multithreaded behavior**, and introduces several new features for working with multi-monitor systems. It also lays groundwork for upcoming improvements planned for **MSS 11.0**, while remaining fully backward-compatible.

If your code works with previous versions of MSS, **it should continue to work unchanged in 10.2.0.**

---

# Highlights

## Demo Applications

The repository now includes several **full demo programs** under `demos/` showing common screenshot-processing workflows built on MSS.

These examples are intended as **learning resources and reference implementations**.  The demos include extensive comments explaining the pipeline architecture and performance considerations involved in real-world screenshot processing, as well as how to use MSS with several popular libraries.

Included demos:

### Video Recorder
Records the screen to a video file using MSS frames.

### TinyTV Streamer
Streams the screen as **MJPEG** to a TinyTV device.

### Cat Detector
Demonstrates real-time computer vision by detecting cats appearing on the screen.

While playful, these examples illustrate techniques for:

- video capture
- streaming
- real-time analysis of screenshots
- multithreaded pipelining
- integration with PyAV, Pillow, and PyTorch

## Richer Monitor Metadata

**If you currently use `sct.monitors[1]` to select the primary display, you may prefer the new `sct.primary_monitor` property.**

Monitor dictionaries now include additional metadata to help applications identify displays reliably:

- `is_primary` — whether this monitor is the primary display
- `name` — human-readable device name
- `unique_id` — stable identifier for the display

These values make it easier to:

- detect the primary monitor
- select a specific display across runs
- handle dynamic multi-monitor configurations

These new values are only present if they can be detected.  In some cases (such as with a very old monitor), they may not be available.

A new convenience property has also been added:

```python
sct.primary_monitor
```

This returns the monitor dictionary corresponding to the system’s primary display.

Currently available on:

- **Windows**
- **Linux**

Support for macOS will be added in the future.

## Multithreading Improvements

Multithreaded usage of MSS has been improved and clarified.

In 10.2.0:

- **An `MSS` instance can safely be passed between threads**
- **Calls to `grab()` on the same `MSS` instance remain serialized**, but are now guaranteed to be safe
- **Multiple `MSS` instances can capture concurrently**, allowing parallel capture across threads

Previously, some internal locking effectively serialized capture across all MSS usage. In 10.2.0, locking is now **per instance**, allowing independent MSS objects to perform captures simultaneously.

The [documentation](https://python-mss.readthedocs.io/usage.html#multithreading) has also been expanded to describe MSS’s supported multithreading guarantees.

On Linux, the new **XCB-based backend** further improves the reliability of multithreaded usage compared to the previous Xlib-based implementation.

---

## Improved Linux Capture Backend

The Linux capture implementation has been significantly modernized to reduce capture overhead and improve multithreaded reliability.

### New XCB Backend

MSS now includes an **XCB-based backend stack**, replacing the previous Xlib-based implementation. XCB provides more predictable thread-safety and improves the reliability of multithreaded capture.

The previous Xlib implementation remains available as a fallback for systems where the XCB backend cannot be used. See [the GNU/Linux usage documentation](https://python-mss.readthedocs.io/usage.html#gnu-linux) for configuration details.

### Shared-Memory Capture (XShm)

Linux now uses **`XShmGetImage`** by default, allowing MSS to capture screenshots using the X11 shared-memory extension when it is available.

With this method, the X server writes pixel data directly into a shared memory buffer provided by the client, avoiding the extra copy required by the traditional `XGetImage` path. This reduces overhead during capture and dramatically improves performance for applications that take screenshots frequently.

If shared memory is not available, MSS automatically falls back to `XGetImage`.

### Capture Performance

The new Linux backend can significantly reduce screenshot capture overhead.

In local testing (local desktop system, Debian testing, X11, 4K display), a tight loop capturing the full screen (1000 iterations, best of three runs) improved from:

```
10.1.0: 46.2 ms per screenshot
10.2.0:  9.48 ms per screenshot
```

This represents roughly a **5× reduction in capture time** in that environment.

The improvement comes primarily from the new backend architecture and the use of the **X11 shared-memory extension (`XShmGetImage`)**, which avoids an additional memory copy when transferring pixel data from the X server.

Actual performance improvements will vary depending on factors such as:

- display resolution
- X server configuration
- hardware
- whether the shared-memory capture path is available

## Windows Capture Improvements

The Windows screenshot implementation now uses **`CreateDIBSection`** instead of `GetDIBits`.

This reduces memory overhead and improves reliability during long capture sessions.

Additional improvements include:

- improved Win32 error handling and diagnostics
- fixes for capture failures during extended recordings

## macOS Stability Fix

A memory leak in the macOS backend has been fixed.

---

# Deprecations and Upcoming Changes (Planned for 11.0)

This release introduces deprecations that will take effect in **MSS 11.0**.

These changes are intended to improve:

- API clarity
- type safety
- future GPU capture support
- internal performance

Most users will **not need to change anything immediately**.

If you are unsure whether you are affected, search your codebase for the names mentioned below.

## Deprecated Attribute

### `mss.ScreenShot.raw`

**Status:** Deprecated
**Removal:** 11.0

Use `bgra` instead.

```python
# Before
data = screenshot.raw

# After
data = screenshot.bgra
```

Important differences:

- `raw` is **mutable**
- `bgra` is **immutable**

In 11.0, screenshot pixel buffers will no longer support in-place modification.

If your application relies on modifying screenshot pixels directly, please [open an issue](https://github.com/BoboTiG/python-mss/issues/new) so we can discuss your use case.

## Screenshot Class Changes

To prepare for future GPU capture support, the screenshot class hierarchy will change in **11.0**.

`ScreenShot` will become a base class with specialized implementations:

```
ScreenShot
 └── ScreenShotCPU
```

In preparation for this change, **10.2.0 introduces `ScreenShotCPU`** as a subclass of the current `ScreenShot` class.

Users who rely on type annotations can begin migrating now:

```python
foo: mss.ScreenShotCPU = sct.grab()
```

This annotation works in both **10.2.x** and **11.x**.

If you do not use explicit type annotations, **no changes are required**.

## Monitor Objects

In 11.0, monitor dictionaries will become a dedicated **`Monitor` class**.

To maintain compatibility:

- dictionary-style access will continue to work

```python
monitor["left"]
monitor["top"]
```

- `grab()` will continue accepting dictionaries

If you use type annotations, you can switch to the provided `Monitor` type:

```python
from mss.models import Monitor
```

This works in both **10.2.x** and **11.x**.

## `bgra` Return Type

In 11.0, `ScreenShot.bgra` will return a **bytes-like object**, not necessarily a `bytes` instance.

Code that treats the result as binary data will continue to work.

If your code checks for an exact type, update it to accept bytes-like objects:

```python
isinstance(data, (bytes, bytearray, memoryview))
```

## `cls_image` Constructor Behavior

The constructor signature used when providing a custom screenshot class via `cls_image` may change in 11.0.

If you implement a custom class, ensure your constructor accepts flexible arguments:

```python
def __init__(self, *args, **kwargs):
```

If you do not use `cls_image`, you are unaffected.

## Internal Platform Attributes

The following attributes were never intended as public API and will be removed in 11.0.

If you need these system libraries, load them directly via `ctypes`.

### Windows
- `mss.windows.MSS.user32`
- `mss.windows.MSS.gdi32`

### macOS
- `mss.darwin.MSS.max_displays`

Most users are **not affected**.

---

If you believe an upcoming change could impact your workflow, please [open an issue](https://github.com/BoboTiG/python-mss/issues/new) so we can discuss it before 11.0.
