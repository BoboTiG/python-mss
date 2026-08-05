---
orphan: true
---

# Source-bound capture API

Status: design proposal for issues [#470](https://github.com/BoboTiG/python-mss/issues/470) and
[#544](https://github.com/BoboTiG/python-mss/issues/544).

Decisions below reflect discussion on #544 through 2026-08-01. Sections marked **Deferred** are not part of v1.

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
session.list_monitors()  # Returns tuple[Monitor, ...]; no desktop entry
session.list_windows()   # Returns tuple[Window, ...]
```

For typing we will mark the return type as `Sequence` for design freedom but
we will return a tuple so the snapshot cannot be resized or reassigned in place.

Sources returned by a session carry private provenance. `create_capture()`
accepts only a source returned by that same session. A manually constructed
`Monitor` will no longer be useful as geometry, legacy `MSS.grab()` accepts
dictionaries (for backwards compatibility) and recently introduced `Region`
type. See PR #566. Passing a foreign or manually constructed source to
`create_capture()` raises `ValueError`.

Inputs are always display-oriented: a 90°-rotated 1920×1080 panel is addressed
as width 1080, height 1920. In rare cases a backend may operate in backbuffer
orientation (scanout) that has a different rotation than the display
orientation. When we encounter such a backend we will add an attribute to it
so that users can query for this behavior and therefore interpret the captured
image correctly. We can also add convenience flags to have MSS perform
a rotation so the image is returned display-oriented. We do not need to finalize
this design now. We can cross this bridge when we get there (most likely DXGI). 

```python
class PixelSpace(Enum):
    LOGICAL = auto()   # points / DIPs / nominal display units
    PHYSICAL = auto()  # backing-store / framebuffer pixels
```

Pixel space is not selected by the caller. It is determined by the platform and any process or
thread DPI configuration established by the application. MSS does not change process DPI awareness implicitly,
but it does offer a utility function on Windows, for the user's convenience.

Enumerated source geometry uses the session's effective pixel space:

```python
session.pixel_space  # PixelSpace
source.bounds        # Region in session.pixel_space
```
The session therefore informs the user of the pixel_space being used. This should be fixed for the
lifetime of an MSS session. Applications must not change their pixel space while the session or its captures are active. MSS may detect such a change and raise an exception.

Typical behavior is:

```text
Windows          Determined by the application's DPI-awareness context
Linux/X11        PHYSICAL
Linux/Wayland    PHYSICAL capture-buffer pixels
macOS            LOGICAL
```

The initial API does not resample to produce another space. Capture geometry remains in `session.pixel_space`, while
returned image buffers always contain physical pixels. The result metadata described below provides the mapping between
the two.

### Monitors

`Monitor` is introduced first as a focused change for #470. It is a frozen,
slotted dataclass with required geometry and optional standard metadata such as
`is_primary`, `name`, `unique_id`, and Linux `output`. It supports attributes
and retains string-key access temporarily for migration, but does not promise
the complete `Mapping` interface.

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

Window identity is native and does not silently follow an application through native window recreation. Destroying a
window ends that source identity; a capture does not retarget even if another window later has the same title, PID,
class, or native ID.

## Capture creation

```python
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
    with_cursor: bool | None = None,
    area: WindowArea | None = None,
) -> Capture: ...
```

The caller does not choose logical or physical coordinates. The resolved space is inspectable through
`session.pixel_space` and remains stable for the lifetime of the session and therefore the capture.

`area` is valid only with a `Window` source. It must be `None` for `Monitor` and `Desktop`. For a `Window`, `None`
resolves to `WindowArea.FULL`, the v1 default. Region coordinates on later `grab` calls are relative to the chosen
extent: with `CLIENT`, `(0, 0)` is the client/content origin; with `FULL`, `(0, 0)` is the full native window origin.

`FULL` means the native frame rectangle, including title bars, borders, menus, and other non-client chrome. It excludes
compositor effects outside that rectangle, such as drop shadows, glow, capture-selection borders, and other external
decoration. A backend is eligible only if it can honor the requested extent. `CLIENT` is an optional backend capability;
an explicit request raises `BackendUnavailableError` if no eligible backend can guarantee the client extent. MSS does
not approximate it from platform-specific decoration sizes.

`with_cursor` is tri-state for backend selection:

```text
True   cursor must be included; only backends that can guarantee that are eligible
False  cursor must be excluded; same filter the other way
None   don't care (default); auto may pick the best otherwise-eligible backend;
       cursor presence is unspecified
```

When cursor inclusion is required (`True`), cursor pixels are composited only where they intersect the final clipped
output.

Source type, cursor preference, and window area are requirements expressed by the capture request. Pixel space is an
observed property, not a capture request. Streaming capabilities are deferred with `frames()` and are not part of the
v1 capture-creation API.

### System-picker creation

Application-selected sources use `create_capture()`. User-selected surfaces use a system picker and are bound directly
to the returned capture:

```python
class PickerTarget(Flag):
    WINDOW = auto()
    MONITOR = auto()


def create_capture_from_picker(
    self,
    *,
    target_hint: PickerTarget = PickerTarget.WINDOW | PickerTarget.MONITOR,
    backend: str = "auto",
    with_cursor: bool | None = None,
    window_area: WindowArea = WindowArea.FULL,
    parent_window: object | None = None,
) -> Capture | None: ...
```

```python
capture = session.create_capture_from_picker(
    target_hint=PickerTarget.WINDOW,
    with_cursor=True,
)
if capture is None:
    return  # User cancelled.
```

The method blocks while the system picker is open and returns when the user
selects a source or the platform reports that the user cancelled. `None` means
cancellation only. Failure to create or operate the picker, loss of the portal
or native service, permission failure, an invalid platform response, and failure
to initialize the selected capture raise an exception. It has no timeout.

If no eligible picker backend can be initialized before UI is presented,
`BackendUnavailableError` reports attempted-provider context in the same way as
`create_capture()`. After a picker backend has presented UI, an abnormal picker
exit or failure to initialize the selected source raises `PickerError` and
chains the native cause where available. Automatic backend fallback does not
occur after UI has been presented.

`target_hint` is a best-effort hint about which source categories to present. Its default requests no narrowing. A
backend narrows the picker when its platform API supports doing so, but the hint does not participate in backend
eligibility or fallback. A backend may ignore it and offer a broader set of categories; a selection outside
the hint is accepted normally.

The platform picker determines how choices are presented. One surface is selected. The selected item and associated
resources are not exposed as a public `CaptureSource`.
`window_area` applies only if the user selects a window and is irrelevant when a
monitor is selected. A picker backend is eligible only if it can honor
`window_area` whenever it offers window selection. `parent_window` is the
platform-specific parent handle for the picker. MSS presents at most one picker
and does not reprompt after selection if capture initialization fails.

This path is required by portal-only Wayland. In the future we may also offer it for Windows WGC and macOS
ScreenCaptureKit. Although WGC,
ScreenCaptureKit, and the Wayland portal complete selection asynchronously at the platform level, the initial public API
is synchronous. A `create_capture_from_picker_async()` variant may be added later without changing the synchronous API.

### Regions

`region` is **not** a `create_capture` argument. It is optional on `grab()`:

```python
capture.grab()
capture.grab(region=Region(left=10, top=20, width=640, height=480))
```

`None` captures the full source extent (subject to `area` for windows). Region may differ across `grab` calls.
Coordinates and clipping use `capture.pixel_space`.

Region fields are integers. Negative `left` and `top` values are valid. Width and height must be positive; zero or a
negative value raises `ValueError`. The effective rectangle is recomputed for each acquisition against the
capture-local extent:

```python
source_extent = Region(left=0, top=0, width=source_width, height=source_height)
effective = requested_region.intersection(source_extent)
```

`image.bounds` describes the effective clipped rectangle in `capture.pixel_space`. A region with an empty intersection
raises `ValueError`. If the source itself currently has an empty extent, frame acquisition is temporarily unavailable
and follows the `timeout` behavior described below. V1 does not create zero-sized `ScreenShot` objects.

Every v1 CPU backend must support a different valid region on each `grab()` call, either through native cropping or by
cropping inside MSS. Auto-selection never chooses a backend that rejects this normal `Capture` operation.

Insets / negative width-height as a crop-from-edges sugar remain deferred.

### Backend selection

```python
capture.backend  # "xshmgetimage", "gdi", ...
```

For `backend="auto"`, MSS filters the platform providers by source and capture configuration, then tries eligible
providers in implementation-defined order. If none succeeds, `BackendUnavailableError` reports useful attempted-provider
context in its message without making a structured failure history part of the public API.

An explicit backend never falls back. Automatic fallback occurs only during capture creation; recovery never changes a
capture's provider. Auto-selection order is an implementation detail and may improve between releases. Users who need a
specific provider select it explicitly. Providers may be changed or disabled at any time for correctness, security, or
platform compatibility.

## Results

The result type remains **`ScreenShot`**. It is not replaced by a separate `Frame` type.

```python
image.bounds  # Effective captured Region in capture.pixel_space
image.pos     # Origin of image.bounds in session-global coordinates
image.size    # Width and height of the returned buffer in physical pixels
```

`image.bounds` uses session-global coordinates and records the exact source rectangle represented by the result.
`image.pos` is its top-left origin and therefore also uses `capture.pixel_space`. `image.size`, `image.width`,
`image.height`, buffer dimensions, row stride, and array/tensor shapes always describe physical pixels. Each result
contains one physical buffer, never logical and physical copies.

`source.bounds` and `capture.source_bounds` use session-global desktop coordinates in `capture.pixel_space`. A region
passed to `grab()` is capture-local. `image.bounds` is the effective clipped region translated by the origin of
`capture.source_bounds`; `image.pos` is the origin of that translated rectangle. For `WindowArea.CLIENT`,
`capture.source_bounds` describes the global client/content rectangle; for `WindowArea.FULL`, it describes the global
native frame rectangle.

When `capture.pixel_space` is `PHYSICAL`, the width and height of `image.bounds` equal `image.size`. On macOS, capture
geometry is `LOGICAL` while `image.size` remains physical and may therefore differ. The exact per-result mapping is
available without a separate scale-factor API:

```python
scale_x = image.size.width / image.bounds.width
scale_y = image.size.height / image.bounds.height
```

Callers must not combine `image.pos` and `image.size` as though they form a rectangle in one coordinate space; use
`image.bounds` for source geometry and `image.size` for indexing the pixel buffer.

Future direction (not v1): `ScreenShot` as a base with `ScreenShotCpu` and `ScreenShotGpu` subclasses sharing common
attributes; CPU and GPU results expose different buffers.

### Buffer layout

`ScreenShot` does **not** require tightly packed rows. Backends may return a native stride/pitch. Contiguous packed
BGRA is obtained lazily via `.bgra` (may copy). NumPy/PIL/PyTorch and similar consumers can use the native layout
directly when they support strides.

Exact pixel-format negotiation (HDR, YUV, etc.) is deferred with GPU work.

### Timing, statistics, and capabilities — **Deferred**

`CaptureCapability`, `FrameTiming`, and `CaptureStatistics` are deferred past the first cut of the source-bound API.
They can be designed with the first operation that consumes them rather than becoming speculative v1 public surface.

### `cls_image`

Dropped from the new API. Legacy `MSS.cls_image` may remain on the deprecated path; source-bound capture does not grow
an equivalent.

## Pull and continuous capture

```python
def grab(
    self,
    region: Region | None = None,
    *,
    timeout: float | None = None,
) -> ScreenShot: ...
```

`grab()` returns a newly constructed current image whenever the backend can complete the request. Repeated calls may
contain identical pixels. It does not promise a distinct source presentation, a particular rate, or no-drop delivery.

`timeout` is a non-negative duration in seconds. `None` (the default) waits indefinitely, and zero performs one
immediate acquisition attempt without waiting. If the backend does not provide usable pixels before the deadline,
`grab()` raises `CaptureTimeoutError`; the capture remains `OPEN` and may be used again. This deadline includes time
spent recovering from temporary provider failures. A negative timeout raises `ValueError`.

MSS does not return a cached prior image merely to satisfy a timed acquisition. The caller can retain the last
successful image and decide whether to reuse it after `CaptureTimeoutError`. Pixel contents are not an availability
signal: an all-black or unchanged image may be a valid current result and is returned normally.

### `frames()` — **Deferred**

The streaming API, buffering, timeouts, update notifications, and concurrency rules will be designed together in a
separate change. Adding `frames()` later does not require changing source-bound capture creation or `grab()`.

## Lifetime and recovery

`Capture` is an idempotent context manager: `__exit__` closes; `close()` may be called again with no effect.

```python
with session.create_capture(source) as capture:
    image = capture.grab()

capture.close()  # No effect, was called by context close above and is idempotent
```

The caller owns captures and should close them promptly. The session weakly tracks live captures and closes them before
closing shared platform resources. Returned image storage remains valid after both capture and session closure.

```text
OPEN
├── source removed ─────────────> REMOVED
├── unrecoverable provider error ─> FAILED
└── close() ────────────────────> CLOSED
```

MSS recovers transparently while it can prove the same source identity and capture contract remain available. Examples
include device reset, DXGI duplication invalidation, frame-pool recreation, window resizing, and resolution or
orientation changes for the same monitor. Recovery stays within the selected provider and preserves required
capabilities.

A minimized, hidden, or temporarily unavailable window remains `OPEN`. Window destruction and monitor unplug are
terminal source removal. Recreated windows, reconnected monitors, matching titles, matching geometry, and reused list
indices do not silently retarget a capture. `Desktop` persists across monitor-topology changes.

On Windows, minimizing an exclusive-fullscreen application or locking the user session may stop usable frames or make
GDI, D3D, DXGI, or frame-pool resources temporarily unusable without destroying the captured window. These are
temporary provider conditions: `grab()` follows its timeout behavior while MSS attempts recovery within the selected
provider. Capture can resume after restore or unlock if MSS can prove that the same source identity remains. The secure
lock desktop is not a replacement capture source. If the application destroys and recreates its native window during
that transition, the original source instead becomes `REMOVED`.

`REMOVED` deliberately avoids the Direct3D "lost device" terminology. Device loss and desktop-duplication invalidation
are recoverable provider conditions when the source still exists; they are not terminal source removal.

## Exceptions

```text
MSSError
├── ScreenShotError                       legacy API
├── SessionClosedError
├── SessionModeError                      legacy/source-bound API paths mixed
├── SourceEnumerationUnsupportedError
├── WindowSelectionError
├── BackendUnavailableError
├── PickerError                             abnormal picker exit or selected-source initialization failure
└── CaptureError
    ├── CaptureTimeoutError                retryable; capture remains OPEN
    ├── CaptureSourceRemovedError          terminal REMOVED
    └── CaptureClosedError
```

`MSSError` is the package top-level exception. `ScreenShotError` remains for the legacy path only; the new API is not
rooted at `ScreenShotError`.

Invalid argument types use `TypeError`; invalid values use `ValueError`. Window-selector callback exceptions propagate
unchanged. `PickerError` and `CaptureError` chain their native causes where available.

## Compatibility and deferred work

The deprecated `MSS.grab()`, `MSS.monitors`, `save()`, and `shot()` retain their current desktop-rectangle semantics
(including today's macOS nominal-resolution default and packed `ScreenShot` buffers). `MSS.monitors` returns the new
immutable `Monitor` objects, including the virtual-desktop entry at index zero; temporary string-key access provides the
migration bridge. Legacy `MSS.grab()` accepts those objects as well as current user-created dictionaries and PIL-style
tuples. The legacy and new paths must not be mixed on one `MSS` session. A session is initially uncommitted; its first
legacy or new operation commits it to that path for its lifetime. Using an API from the other path afterward raises
`SessionModeError`.

The legacy backend is initialized lazily by the first legacy operation. Constructor-level `backend=` and
`with_cursor=` configure only that path; they do not initialize it. New source enumeration and capture creation belong
to the source-bound (new) path, including `desktop`, `list_monitors()`, `list_windows()`, `find_window()`, `create_capture()`,
and `create_capture_from_picker()`. Compatibility helpers do not call deprecated public methods internally.

On Windows, only initialization of the legacy GDI path attempts to establish the process DPI awareness required by its
existing physical-desktop coordinate contract. Source-bound session creation and use never change process or thread DPI
awareness implicitly. We will improve the legacy GDI initialization so it validates the resulting awareness and raises `ScreenShotError` if an
incompatible value was already established by the application manifest or by other code in the process, or if Windows
otherwise refuses the requested configuration. An already-established compatible value is accepted.

### Settled for this revision

- Session + source-bound `Capture`; region on `grab`, not `create_capture`
- Sources carry private session provenance; manually constructed geometry is not a capture source
- Pixel space is platform/process determined and inspectable, not caller-selectable
- Source and image bounds are session-global; requested regions are capture-local
- `image.size` and buffer shapes are always physical; `image.bounds` maps them to the capture's coordinate space
- Synchronous `create_capture_from_picker`; best-effort `target_hint`, no hard target-category filter or public
  intermediate picked-source object
- Picker cancellation returns `None`; every abnormal picker exit raises an exception
- `WindowArea` instead of `client_area_only`; `FULL` is the portable v1 default
- Picker `window_area` is conditional on the user selecting a window
- `with_cursor: bool | None` for auto backend selection
- `find_window` only (no `get_window`); window equality by identity
- Enumeration snapshots as `tuple[...]`
- Dynamic region cropping is required for every v1 CPU backend
- Non-positive and completely clipped regions do not produce empty screenshots
- Keep `ScreenShot`; allow strides; lazy packed `.bgra`
- No `cls_image` on the new path
- Per-call `grab(timeout=...)`; timeout is retryable and never returns an MSS-cached prior image
- Terminal `REMOVED` is distinct from recoverable provider or device unavailability
- Expose only the selected `capture.backend`; auto-selection order remains an implementation detail
- `MSSError` as the new-API exception root
- Legacy and source-bound operations cannot be mixed in one session; legacy initialization remains lazy

### Deferred

- `frames()` and its buffering, timeout, notification, capability, timing, statistics, and concurrency contracts
- Native-stride and other non-packed CPU result layouts
- `ScreenShotCpu` / `ScreenShotGpu` split and GPU result types
- Richer pixel formats / color spaces
- Region insets (negative width/height syntactic sugar)
- Structured backend-attempt diagnostics after successful auto-selection

## Implementation task list

Each task is intended to be reviewable independently and should include focused tests and documentation for its public
behavior.

### Task 1: Immutable `Monitor` model (#470)

- Replace the public monitor dictionary returned by `MSS.monitors` with a frozen, slotted `Monitor` dataclass.
- Include required geometry and the existing optional standard metadata.
- Preserve temporary string-key access such as `monitor["width"]`; do not promise the complete `Mapping` interface.
- Keep legacy `MSS.grab()` support for user-created monitor/region dictionaries and PIL-style tuples.
- Update platform enumeration, compatibility code, typing, tests, examples, and migration documentation.

### Task 2: Platform session and source enumeration

- Split shared platform/session resources from legacy capture initialization.
- Add `Desktop`, session-bound `Monitor`, and `Window` source provenance.
- Add `pixel_space`, `desktop`, `list_monitors()`, and `list_windows()` with immutable snapshot semantics.
- Define platform enumeration support and `SourceEnumerationUnsupportedError` behavior.
- Validate that foreign and manually constructed sources cannot enter the new capture path.

### Task 3: `find_window()` convenience

- Implement `find_window()` strictly on top of `list_windows()`; it does not participate in backend selection or capture
  lifetime.
- Add the built-in ID, title, and property selectors described above.
- Preserve exact, case-sensitive string matching, regular-expression `search()`, `None` for no match, and
  `WindowSelectionError` for ambiguous built-in matches.
- Validate custom-selector results and propagate custom exceptions unchanged.

### Task 4: Source-bound CPU capture core

- Add `Region`, `WindowArea`, `Capture`, `create_capture()`, and the v1 exception hierarchy.
- Implement context-manager lifetime, idempotent close, source ownership checks, and stable result-buffer lifetime.
- Implement global/source-local coordinate rules, physical result sizes with `image.bounds` mapping, clipping,
  positive-size validation, dynamic per-grab regions, and per-call acquisition timeouts.
- Exercise the public contract against small fake implementations before adding platform providers.

### Task 5: Platform capture providers and auto-selection

- Implement or adapt CPU providers for the supported X11, Windows, and macOS source types.
- Require each eligible provider to honor source type, cursor preference, window area, and dynamic region cropping.
- Add `backend="auto"`, explicit backend selection, fallback during creation, and `capture.backend` introspection.
- Keep provider ordering and successful fallback details internal.
- Test source removal, retryable frame unavailability, resizing, provider failure, logical-to-physical result mapping,
  and the no-silent-retarget rule per platform.

### Task 6: System-picker capture

- Add the synchronous picker path and cancellation/error semantics.
- Implement portal-based Wayland capture first; add other platform pickers only when their providers are implemented.
- Apply `target_hint` where supported; enforce conditional `window_area`, cursor requirements, parent-window handling,
  and no fallback after UI is shown.
- Keep asynchronous picker APIs deferred.

### Task 7: Legacy migration and release integration

- Initialize the legacy backend lazily and enforce the one-session/one-mode rule.
- Keep legacy coordinate, macOS resolution, cursor, and packed-buffer behavior unchanged.
- Ensure `save()` and `shot()` use private compatibility helpers without emitting misleading internal deprecation warnings.
- Add deprecation notices, upgrade documentation, release notes, and the required AI-assistance disclosure in the pull
  request template.
