---
orphan: true
---

# Source-bound capture API

Status: design proposal for issues [#470](https://github.com/BoboTiG/python-mss/issues/470) and
[#544](https://github.com/BoboTiG/python-mss/issues/544).

## Overview

`MSS` is a platform session. It enumerates sources and creates source-bound `Capture` objects. CPU captures continue
returning `ScreenShot` objects.

```python
with MSS() as session:
    monitor = session.list_monitors()[0]

    with session.create_capture(monitor) as capture:
        image = capture.grab()
```

The source types are explicit. A region restricts a source; it is not itself a source.

```python
CaptureSource = Desktop | Monitor | Window


@dataclass(frozen=True, slots=True)
class Region:
    left: int
    top: int
    width: int
    height: int
```

```python
capture = session.create_capture(
    session.desktop,
    region=Region(left=10, top=20, width=640, height=480),
)
```

## Public types

### Sources

`Desktop`, `Monitor`, and `Window` are read-only. Enumeration returns a new snapshot on each call.

```python
session.desktop
session.list_monitors()  # tuple[Monitor, ...]; no desktop entry
session.list_windows()   # tuple[Window, ...]
```

Source coordinate spaces use physical pixels:

```text
Desktop  virtual-desktop coordinates; its origin may be negative
Monitor  (0, 0) is the displayed monitor's upper-left pixel
Window   (0, 0) is the selected window area's upper-left pixel
```

Displayed orientation determines source dimensions. Callers do not apply a rotation transform.

`Monitor` supports attributes. It may retain string-key access temporarily for migration.

```python
monitor.width
monitor["width"]  # Compatibility access.
```

### Windows

```python
class Window:
    id: int
    title: str
    pid: int | None
    exe: str | None
    class_name: str | None
    bounds: Region
    visible: bool
    minimized: bool
    attributes: Mapping[str, object]
```

Core properties describe the enumeration snapshot. Expensive properties such as `exe` may be loaded lazily and return
`None` if the process disappears or access is denied. A `Window` belongs to the session that enumerated it. Window
objects initially use object identity for equality; callers can compare native IDs explicitly.

`list_windows()` includes top-level application windows and minimized windows. Hidden windows require
`include_hidden=True`. Child controls, shell surfaces, menus, tooltips, and similar transient windows are excluded where
the platform can identify them reliably.

```python
WindowSelector = Callable[[tuple[Window, ...]], Window | None]


def find_window(
    self,
    selector: WindowSelector,
    include_hidden: bool = False,
) -> Window | None: ...


def get_window(
    self,
    selector: WindowSelector,
    include_hidden: bool = False,
) -> Window: ...
```

MSS supplies selectors for common cases:

```python
session.find_window(window_by_id(hwnd))
session.find_window(window_by_title("Game"))
session.find_window(window_by_title(re.compile(r"(^| - )Firefox$")))
session.find_window(window_by_properties(pid=12345, exe="game.exe"))
session.find_window(lambda windows: choose_window(windows))
```

Built-in selectors return `None` for no match and raise `WindowSelectionError` for multiple matches. String matching is
exact and case-sensitive; regular expressions use `search()`. A custom selector must return one of the supplied windows
or `None`, and its exceptions propagate unchanged. `get_window()` converts a `None` result to `WindowSelectionError`.

Window identity is native and does not silently follow an application through native window recreation. A destroyed
window remains lost even if another window later has the same title, PID, class, or native ID.

## Capture creation

```python
class CaptureCapability(Flag):
    NONE = 0
    FRAME_NOTIFICATIONS = auto()
    PRESENTATION_TIMESTAMPS = auto()
    SOURCE_MISSED_FRAME_COUNT = auto()
```

```python
def create_capture(
    self,
    source: CaptureSource,
    *,
    region: Region | None = None,
    backend: str = "auto",
    required_capabilities: CaptureCapability = CaptureCapability.NONE,
    with_cursor: bool = False,
    client_area_only: bool = False,
) -> Capture[ScreenShot]: ...
```

`client_area_only` is valid only for a `Window`. Its default captures the complete native window, including non-client
decorations. Regions are relative to the selected complete-window or client-area extent.

`with_cursor` is strict. `True` guarantees cursor inclusion and `False` guarantees exclusion. Automatic backend
selection considers only providers that can satisfy the requested value. Cursor pixels are composited only where they
intersect the final clipped output. With cursor inclusion enabled, cursor movement, shape changes, and visibility
changes count as output updates for `frames()`.

Configuration is separate from capability flags: source type, cursor inclusion, client-area capture, regions, and CPU
output are requirements already expressed by the capture request.

### Regions

Region fields are integers. Negative `left` and `top` values are valid. Negative width or height raises `ValueError`;
zero is valid. The effective rectangle is recomputed for each acquisition:

```python
effective = requested_region.intersection(source.bounds)
```

The returned image describes the clipped rectangle:

```python
image.pos == Pos(effective.left, effective.top)
image.size == Size(effective.width, effective.height)
```

A completely clipped region returns an empty `ScreenShot` without a native pixel copy. Continuous capture still
observes source updates because a resized source may make the region nonempty later. For an empty intersection, the
position is the requested origin clamped to the nearest source boundary.

### Backend selection

```python
@dataclass(frozen=True, slots=True)
class Backend:
    name: str
    capabilities: CaptureCapability


class BackendFailure(NamedTuple):
    name: str
    reason: str
```

```python
capture.backend.name
capture.backend.capabilities
capture.backend_failures  # tuple[BackendFailure, ...]
```

For `backend="auto"`, MSS filters a documented platform/source priority list by the capture configuration and required
capabilities, then tries eligible providers in order. `backend_failures` records each higher-priority provider considered
before the successful one and why it could not be used. If none succeeds, `BackendUnavailableError.failures` contains
the same records.

An explicit backend never falls back. Automatic fallback occurs only during capture creation; recovery never changes a
capture's provider. Priority does not change in patch releases. Minor releases append new providers behind established
eligible defaults; established defaults may be reordered in a major release. Providers may be disabled sooner for
correctness, security, or platform compatibility.

## CPU results and timing

The default result remains `ScreenShot`. It contains CPU-addressable, tightly packed, top-to-bottom BGRA/BGRX bytes:

```text
row stride  width * 4
channels    B, G, R, A/X
alpha       not guaranteed meaningful
```

Backends may acquire another native format but convert as necessary before returning a CPU `ScreenShot`.

```python
@dataclass(frozen=True, slots=True)
class FrameTiming:
    sequence: int
    source_generation: int
    source_sequence: int | None
    presented_at_ns: int | None
    acquired_at_ns: int
    ready_at_ns: int
    delivered_at_ns: int


@dataclass(frozen=True, slots=True)
class CaptureStatistics:
    acquired_frames: int
    delivered_frames: int
    dropped_frames: int
    source_missed_frames: int | None
```

Built-in `ScreenShot` results from the new API always have `image.timing`; directly constructed and legacy screenshots
may have `timing=None`. All times use one documented monotonic nanosecond clock. `presented_at_ns` is `None` unless the
backend supplies a reliable presentation time in that clock domain. Acquisition time is never reported as presentation
time.

`sequence` is capture-wide and monotonic across generator restarts and native recovery. Gaps reveal MSS-side drops.
`source_sequence` belongs to `source_generation`; the generation increments when recovery changes the native sequence
domain. Repeated `grab()` results receive new MSS sequences but may share a source sequence and presentation time.

`capture.statistics` returns an immutable, thread-safe snapshot and remains available after loss, failure, or closure.
`acquired_frames` counts backend updates accepted by MSS, including updates later dropped. `delivered_frames` counts
successful returns and yields. `source_missed_frames` is `None` unless the backend can count misses reliably.

`MSS.cls_image` is snapshotted when a capture is created. The custom image constructor receives:

```python
image_class(data, region, size=actual_size, timing=timing)
```

Custom classes may ignore optional keywords. Changing `session.cls_image` affects future captures, not an existing
capture's result type.

## Pull and continuous capture

```python
image = capture.grab(timeout=1.0)

for image in capture.frames(
    buffer_count=1,
    overflow="drop_oldest",
    timeout=None,
):
    process(image)
```

`grab()` returns a newly constructed current image whenever the backend can complete the request. Repeated calls may
contain identical pixels. It does not promise a distinct source presentation or a particular rate.

`frames()` requires `FRAME_NOTIFICATIONS` and yields only distinct backend-reported output updates. Equal pixels may be
yielded for distinct presentations. MSS does not compare images to infer updates and does not synthesize duplicates.
Calling it without the capability raises `UnsupportedCaptureOperationError`.

`buffer_count` is a positive integer and counts completed images waiting for delivery, excluding native frame pools and
the image held by the consumer. The supported overflow policies are:

```text
drop_oldest  discard the oldest pending image and queue the newest; default
block        stop draining native updates until delivery space is available
```

Native APIs may coalesce or miss updates while blocked; this is not an MSS-side drop. Pending images discarded when a
generator ends count as dropped. Version one has no target-FPS or duplicate-frame video mode.

`timeout` limits each wait for an image. `FrameTimeoutError` terminates that generator but leaves the capture reusable.
`SourceLostError` and `CaptureFailedError` terminate it and leave the capture terminal. Closing the capture ends an
active generator normally.

Only one `frames()` generator may be active. It becomes active on its first iteration. While active, `grab()` or
advancing another generator raises `CaptureBusyError`. Concurrent `grab()` calls are serialized. An individual generator
must not be advanced concurrently from multiple threads.

```python
stream = capture.frames()
try:
    for image in stream:
        if process_and_finish(image):
            break
finally:
    stream.close()  # Required when retaining a generator and leaving early.
```

Closing or exhausting the generator returns the capture to its open state. A timeout permits another generator on the
same capture; source loss requires selecting a source and creating a new capture.

## Lifetime and recovery

`Capture` is an idempotent context manager:

```python
with session.create_capture(source) as capture:
    image = capture.grab()

capture.close()
capture.close()  # No effect.
```

The caller owns captures and should close them promptly. The session weakly tracks live captures and closes them before
closing shared platform resources. Returned image storage remains valid after both capture and session closure.

```text
OPEN
├── first next(frames) ─────────> STREAMING
├── source disappears ──────────> LOST
├── unrecoverable provider error ─> FAILED
└── close() ────────────────────> CLOSED

STREAMING
├── generator close/timeout ────> OPEN
├── source disappears ──────────> LOST
├── unrecoverable provider error ─> FAILED
└── close() ────────────────────> CLOSED
```

MSS recovers transparently while it can prove the same source identity and capture contract remain available. Examples
include device reset, DXGI duplication invalidation, frame-pool recreation, window resizing, and resolution or
orientation changes for the same monitor. Recovery stays within the selected provider and preserves required
capabilities.

A minimized, hidden, or temporarily unavailable window is not lost. `frames()` waits for another update and may time
out; `grab()` may construct a new result from the latest retained source image. Window destruction and monitor unplug
are terminal source loss. Recreated windows, reconnected monitors, matching titles, matching geometry, and reused list
indices do not silently retarget a capture. `Desktop` persists across monitor-topology changes.

Pending delivery images are discarded on native-generation replacement, source loss, or terminal failure. Previously
returned images remain valid. Public timeouts include time spent recovering; `timeout=None` uses finite internal waits
so close, loss, and failure remain observable.

## Exceptions

```text
MSSError
├── ScreenShotError                       legacy API
├── SessionClosedError
├── WindowSelectionError
├── BackendUnavailableError
└── CaptureError
    ├── FrameTimeoutError                 capture reusable
    ├── SourceLostError                   terminal LOST
    ├── CaptureFailedError                terminal FAILED
    ├── CaptureClosedError
    ├── CaptureBusyError
    └── UnsupportedCaptureOperationError
```

Invalid argument types use `TypeError`; invalid values use `ValueError`. Window-selector callback exceptions propagate
unchanged. `CaptureFailedError` chains its native cause.

## Compatibility and deferred work

The deprecated `MSS.grab()`, `MSS.monitors`, `save()`, and `shot()` retain their current desktop-rectangle semantics and
return types. Their legacy backend is initialized lazily. Constructor-level `backend=` and `with_cursor=` configure only
that path; new capture selection belongs to `create_capture()`. Compatibility helpers do not call deprecated public
methods internally.

The new API uses `MSSError` and `CaptureError`; `ScreenShotError` remains the legacy error type.

THis version 1.0 of the new interface deliberately defers GPU result types and more capture-native formats (CPU or GPU).
Internally, capture implementations are generic over their result type and
producer/queue delivery so these improvements can be added later without changes
to the overall design.
