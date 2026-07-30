---
orphan: true
---

# Source-bound capture API

Status: design proposal for issues [#470](https://github.com/BoboTiG/python-mss/issues/470) and
[#544](https://github.com/BoboTiG/python-mss/issues/544).

Decisions below reflect discussion on #544 through 2026-07-30. Sections marked **Open** or **Deferred** are
not settled.

## Overview

`MSS` is a platform session. It enumerates sources and creates source-bound `Capture` objects. Captures return
`ScreenShot` objects (see the Results section below).

```python
with MSS() as session:
    monitor = session.list_monitors()[0]

    with session.create_capture(monitor) as capture:
        image = capture.grab()
        image = capture.grab(region=Region(left=10, top=20, width=640, height=480))
```

The source types are explicit. A region restricts a source at acquisition time; it is not itself a source.

```python
CaptureSource = Desktop | Monitor | Window


@dataclass(frozen=True, slots=True)
class Region:
    left: int
    top: int
    width: int
    height: int
```

## Public types

### Sources

`Desktop`, `Monitor`, and `Window` are read-only. Enumeration returns a new immutable snapshot on each call.

```python
session.desktop
session.list_monitors()  # tuple[Monitor, ...]; no desktop entry
session.list_windows()   # tuple[Window, ...]
```

Return type is `tuple[...]` so the snapshot cannot be resized or reassigned in place.

Inputs are always display-oriented: a 90°-rotated 1920×1080 panel is addressed as width 1080, height 1920. Callers do
not apply a rotation transform.

```python
class PixelSpace(Enum):
    LOGICAL = auto()   # points / DIPs / nominal display units
    PHYSICAL = auto()  # backing-store / framebuffer pixels
```

Enumerated source geometry uses the session's platform-default pixel space:

```python
session.default_pixel_space  # PixelSpace
source.bounds                # Region in session.default_pixel_space
```

The initial API does not provide source-geometry conversion between pixel spaces.

### Monitors

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
`None` if the process disappears or access is denied. A `Window` belongs to the session that enumerated it.

`Window` equality is **object identity**. Native IDs can be recycled after destroy, so `__eq__` is not based on `id`.
Within the same session, callers who need “same OS window” compare `window.id` while that window still exists.

`list_windows()` includes top-level application windows and minimized windows. Hidden windows require
`include_hidden=True`. Child controls, shell surfaces, menus, tooltips, and similar transient windows are excluded where
the platform can identify them reliably.

On platforms that prohibit application-driven enumeration, these APIs raise rather than returning an empty snapshot:

```python
session.list_windows()   # SourceEnumerationUnsupportedError
session.list_monitors()  # SourceEnumerationUnsupportedError
session.desktop          # SourceEnumerationUnsupportedError
```

An empty tuple means enumeration succeeded and found no sources. Portal-only Wayland uses the system-picker path below.

```python
WindowSelector = Callable[[tuple[Window, ...]], Window | None]


def find_window(
    self,
    selector: WindowSelector,
    include_hidden: bool = False,
) -> Window | None: ...
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
or `None`, and its exceptions propagate unchanged.

Window identity is native and does not silently follow an application through native window recreation. A destroyed
window remains lost even if another window later has the same title, PID, class, or native ID.

## Capture creation

```python
class CaptureCapability(Flag):
    NONE = 0
    FRAME_NOTIFICATIONS = auto()
    PRESENTATION_TIMESTAMPS = auto()
    SOURCE_MISSED_FRAME_COUNT = auto()


class PickerTarget(Flag):
    MONITOR = auto()
    WINDOW = auto()


class WindowArea(Enum):
    CLIENT = auto()  # client area / content rect / client window
    FULL = auto()    # entire native window, including non-client chrome
```

```python
def create_capture(
    self,
    source: CaptureSource,
    *,
    backend: str = "auto",
    required_capabilities: CaptureCapability = CaptureCapability.NONE,
    with_cursor: bool | None = None,
    area: WindowArea | None = None,
    pixel_space: PixelSpace | None = None,
) -> Capture: ...
```

`pixel_space=None` resolves to a documented platform default:

```text
Windows          PHYSICAL
Linux/X11        PHYSICAL
Linux/Wayland    PHYSICAL
macOS            LOGICAL
```

`None` does not let the backend choose. The resolved value is stable and inspectable:

```python
capture.pixel_space  # PixelSpace; never None
capture.source_bounds  # Region in capture.pixel_space
session.default_pixel_space
```

Portable applications select a space explicitly. Backend selection rejects providers that cannot produce the requested
space; it never substitutes the other one.

`area` is valid only with a `Window` source. Invalid for `Monitor` / `Desktop`. Region coordinates on later
`grab` calls are relative to the chosen extent: with `CLIENT`, `(0, 0)` is the client/content origin; with
`FULL`, `(0, 0)` is the full native window origin.

**Open:** default for `area` when capturing a window (`CLIENT` vs `FULL`). Lean `CLIENT` unless discussion settles
otherwise.

`with_cursor` is tri-state for backend selection:

```text
True   cursor must be included; only backends that can guarantee that are eligible
False  cursor must be excluded; same filter the other way
None   don't care (default); auto may pick the best otherwise-eligible backend;
       cursor presence is unspecified
```

When cursor inclusion is required (`True`), cursor pixels are composited only where they intersect the final clipped
output, and cursor movement, shape changes, and visibility changes count as output updates.

Configuration is separate from capability flags: source type, cursor preference, window area, pixel space, and regions
are requirements already expressed by the capture request.

### System-picker creation

Application-selected sources use `create_capture()`. User-selected surfaces use an asynchronous system picker and are
bound directly to the returned capture:

```python
async def create_capture_from_picker(
    self,
    *,
    allowed_to_pick: PickerTarget = PickerTarget.MONITOR | PickerTarget.WINDOW,
    backend: str = "auto",
    required_capabilities: CaptureCapability = CaptureCapability.NONE,
    with_cursor: bool | None = None,
    area: WindowArea | None = None,
    pixel_space: PixelSpace | None = None,
    parent_window: object | None = None,
) -> Capture | None: ...
```

```python
capture = await session.create_capture_from_picker(
    allowed_to_pick=PickerTarget.WINDOW,
    with_cursor=True,
    pixel_space=PixelSpace.PHYSICAL,
)
if capture is None:
    return  # User cancelled.
```

`allowed_to_pick` controls the categories offered by the picker; one surface is selected. The selected item, portal
session, authorization, and stream setup are not exposed as a public `CaptureSource`. `area` applies only if the user
selects a window. `parent_window` is the platform-specific parent handle for the picker. Automatic backend fallback may
occur before UI is presented, but MSS presents at most one picker and does not reprompt after selection if capture
initialization fails.

This path is optional on platforms with application-driven selection and required by portal-only Wayland. Although
frame delivery remains synchronous in the first version, picker creation is async because WGC, ScreenCaptureKit, and
the Wayland portal all complete selection asynchronously.

### Regions

`region` is **not** a `create_capture` argument. It is optional on `grab()`:

```python
capture.grab()
capture.grab(region=Region(left=10, top=20, width=640, height=480))
```

`None` captures the full source extent (subject to `area` for windows). Region may differ across `grab` calls.
Coordinates and clipping use `capture.pixel_space`.

Region fields are integers. Negative `left` and `top` values are valid. Negative width or height raises `ValueError`;
zero is valid. The effective rectangle is recomputed for each acquisition:

```python
effective = requested_region.intersection(source_extent)
```

The returned image describes the clipped rectangle. A completely clipped region returns an empty `ScreenShot` without a
native pixel copy. Continuous capture still observes source updates because a resized source may make the region
nonempty later. For an empty intersection, the position is the requested origin clamped to the nearest source boundary.

Insets / negative width-height as a crop-from-edges sugar remain deferred.

If a backend cannot re-crop without reinit, `create_capture` still succeeds; the first incompatible `grab`
request raises `UnsupportedCaptureOperationError`. Prefer backends that can re-crop.

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
capture.backend.capabilities   # introspection / debugging after auto-select
capture.backend_failures       # tuple[BackendFailure, ...]
```

For `backend="auto"`, MSS filters a documented platform/source priority list by the capture configuration and required
capabilities, then tries eligible providers in order. `backend_failures` records each higher-priority provider considered
before the successful one and why it could not be used. If none succeeds, `BackendUnavailableError.failures` contains
the same records.

An explicit backend never falls back. Automatic fallback occurs only during capture creation; recovery never changes a
capture's provider. Priority does not change in patch releases. Minor releases append new providers behind established
eligible defaults; established defaults may be reordered in a major release. Providers may be disabled sooner for
correctness, security, or platform compatibility.

## Results

The result type remains **`ScreenShot`**. It is not replaced by a separate `Frame` type.

```python
image.pixel_space == capture.pixel_space
```

`image.pos`, `image.size`, buffer dimensions, row stride, and array/tensor shapes use that space. Each result contains
one buffer in one space, never logical and physical copies. `capture.source_bounds` gives the captured source extent in
the capture's resolved pixel space.

Future direction (not v1): `ScreenShot` as a base with `ScreenShotCpu` and `ScreenShotGpu` subclasses sharing common
attributes; CPU and GPU results expose different buffers.

### Buffer layout

`ScreenShot` does **not** require tightly packed rows. Backends may return a native stride/pitch. Contiguous packed
BGRA is obtained lazily via `.bgra` (may copy). NumPy/PIL/PyTorch and similar consumers can use the native layout
directly when they support strides.

This would mean that legacy `MSS.grab()` stops returning packed buffers as today, but they can be obtained via attributes as
described above.

Exact pixel-format negotiation (HDR, YUV, etc.) is deferred with GPU work.

### Timing and statistics — **Deferred**

`FrameTiming` and `CaptureStatistics` are deferred past the first cut of the source-bound API. They can be added later
without blocking capture creation, `ScreenShot`, and basic `grab` / `frames`.

### `cls_image`

Dropped from the new API. Legacy `MSS.cls_image` may remain on the deprecated path; source-bound capture does not grow
an equivalent.

## Pull and continuous capture

```python
image = capture.grab()
image = capture.grab(region=...)
```

`grab()` returns a newly constructed current image whenever the backend can complete the request. Repeated calls may
contain identical pixels. It does not promise a distinct source presentation, a particular rate, or no-drop delivery.
**No `timeout` on `grab()`.**

### `frames()` — **Open**

Intent: a streaming path that can deliver consecutive backend updates **without dropping frames** when the consumer
keeps up. `timeout` belongs on this path, not on `grab()`.
Would require us to add a `wait_for_next_frame` or something similar to `grab()`
function.

Only one streaming consumer may be active per capture at a time; details TBD with the `frames()` design. Concurrent `grab()` calls are serialized.

## Lifetime and recovery

`Capture` is an idempotent context manager: `__exit__` closes; `close()` may be called again with no effect.

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
├── source disappears ──────────> LOST
├── unrecoverable provider error ─> FAILED
└── close() ────────────────────> CLOSED
```

MSS recovers transparently while it can prove the same source identity and capture contract remain available. Examples
include device reset, DXGI duplication invalidation, frame-pool recreation, window resizing, and resolution or
orientation changes for the same monitor. Recovery stays within the selected provider and preserves required
capabilities.

A minimized, hidden, or temporarily unavailable window is not lost. Window destruction and monitor unplug are terminal
source loss. Recreated windows, reconnected monitors, matching titles, matching geometry, and reused list indices do
not silently retarget a capture. `Desktop` persists across monitor-topology changes.

## Exceptions

```text
MSSError
├── ScreenShotError                       legacy API
├── SessionClosedError
├── SourceEnumerationUnsupportedError
├── WindowSelectionError
├── BackendUnavailableError
└── CaptureError
    ├── SourceLostError                   terminal LOST
    ├── CaptureFailedError                terminal FAILED
    ├── CaptureClosedError
    ├── CaptureBusyError
    └── UnsupportedCaptureOperationError
```

`MSSError` is the package top-level exception. `ScreenShotError` remains for the legacy path only; the new API is not
rooted at `ScreenShotError`.

Invalid argument types use `TypeError`; invalid values use `ValueError`. Window-selector callback exceptions propagate
unchanged. `CaptureFailedError` chains its native cause.

## Compatibility and deferred work

The deprecated `MSS.grab()`, `MSS.monitors`, `save()`, and `shot()` retain their current desktop-rectangle semantics and
return types (including today's macOS nominal-resolution default and packed buffers). Their legacy backend is
initialized lazily. Constructor-level `backend=` and `with_cursor=` configure only that path; new capture selection
belongs to `create_capture()`. Compatibility helpers do not call deprecated public methods internally.

### Settled for this revision

- Session + source-bound `Capture`; region on `grab`, not `create_capture`
- Explicit logical/physical capture space with platform-dependent `None` default
- Separate `create_capture_from_picker`; no public intermediate picked-source object
- `WindowArea` instead of `client_area_only`; regions relative to the chosen area
- `with_cursor: bool | None` for auto backend selection
- `find_window` only (no `get_window`); window equality by identity
- Enumeration snapshots as `tuple[...]`
- Keep `ScreenShot`; allow strides; lazy packed `.bgra`
- No `cls_image` on the new path
- No `timeout` on `grab()`
- Expose `capture.backend` / `capabilities` / `backend_failures` for introspection
- `MSSError` as the new-API exception root

### Open

- Default `WindowArea` for window captures
- A `frames()` generator design

### Deferred

- `FrameTiming` / `CaptureStatistics`
- `ScreenShotCpu` / `ScreenShotGpu` split and GPU result types
- Richer pixel formats / color spaces
- Region insets (negative width/height syntactic sugar)
