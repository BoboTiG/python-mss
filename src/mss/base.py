# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot
from mss.tools import to_png

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Callable, Iterator

    from mss.models import Monitor, Monitors

    # Prior to 3.11, Python didn't have the Self type.  typing_extensions does, but we don't want to depend on it.
    try:
        from typing import Self
    except ImportError:  # pragma: nocover
        try:
            from typing_extensions import Self
        except ImportError:  # pragma: nocover
            Self = Any  # type: ignore[assignment]

try:
    from datetime import UTC
except ImportError:  # pragma: nocover
    # Python < 3.11
    from datetime import timezone

    UTC = timezone.utc

#: Global lock protecting access to platform screenshot calls.
#:
#: .. versionadded:: 6.0.0
#:
#: .. deprecated:: 10.2.0
#:    The global lock is no longer used, and will be removed in a future release.
#:    MSS objects now have their own locks, which are not publicly-accessible.
lock = Lock()

OPAQUE = 255


class MSSBase(metaclass=ABCMeta):
    """Base class for all Multiple ScreenShots implementations.

    :param backend: Backend selector, for platforms with multiple backends.
    :param compression_level: PNG compression level.
    :param with_cursor: Include the mouse cursor in screenshots.
    :param display: X11 display name (GNU/Linux only).
    :param max_displays: Maximum number of displays to enumerate (macOS only).

    .. versionadded:: 8.0.0
        ``compression_level``, ``display``, ``max_displays``, and ``with_cursor`` keyword arguments.
    """

    __slots__ = {"_closed", "_lock", "_monitors", "cls_image", "compression_level", "with_cursor"}

    def __init__(
        self,
        /,
        *,
        backend: str = "default",
        compression_level: int = 6,
        with_cursor: bool = False,
        # Linux only
        display: bytes | str | None = None,  # noqa: ARG002
        # Mac only
        max_displays: int = 32,  # noqa: ARG002
    ) -> None:
        # The cls_image is only used atomically, so does not require locking.
        self.cls_image: type[ScreenShot] = ScreenShot
        # The compression level is only used atomically, so does not require locking.
        #: PNG compression level used when saving the screenshot data into a file
        #: (see :py:func:`zlib.compress()` for details).
        #:
        #: .. versionadded:: 3.2.0
        self.compression_level = compression_level
        # The with_cursor attribute is not meant to be changed after initialization.
        #: Include the mouse cursor in screenshots.
        #:
        #: In some circumstances, it may not be possible to include the cursor.  In that case, MSS will automatically
        #: change this to False when the object is created.
        #:
        #: This should not be changed after creating the object.
        #:
        #: .. versionadded:: 8.0.0
        self.with_cursor = with_cursor

        # The attributes below are protected by self._lock.  The attributes above are user-visible, so we don't
        # control when they're modified.  Currently, we only make sure that they're safe to modify while locked, or
        # document that the user shouldn't change them.  We could also use properties protect them against changes, or
        # change them under the lock.
        self._lock = Lock()
        self._monitors: Monitors = []
        self._closed = False

        # If there isn't a factory that removed the "backend" argument, make sure that it was set to "default".
        # Factories that do backend-specific dispatch should remove that argument.
        if backend != "default":
            msg = 'The only valid backend on this platform is "default".'
            raise ScreenShotError(msg)

    def __enter__(self) -> Self:
        """For the cool call `with MSS() as mss:`."""
        return self

    def __exit__(self, *_: object) -> None:
        """For the cool call `with MSS() as mss:`."""
        self.close()

    @abstractmethod
    def _cursor_impl(self) -> ScreenShot | None:
        """Retrieve all cursor data. Pixels have to be RGB.

        The object lock will be held when this method is called.
        """

    @abstractmethod
    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB.

        The object lock will be held when this method is called.
        """

    @abstractmethod
    def _monitors_impl(self) -> None:
        """Get positions of monitors.

        It must populate self._monitors.

        The object lock will be held when this method is called.
        """

    def _close_impl(self) -> None:  # noqa:B027
        """Clean up.

        This will be called at most once.

        The object lock will be held when this method is called.
        """
        # It's not necessary for subclasses to implement this if they have nothing to clean up.

    def close(self) -> None:
        """Clean up.

        This releases resources that MSS may be using.  Once the MSS
        object is closed, it may not be used again.

        It is safe to call this multiple times; multiple calls have no
        effect.

        Rather than use :py:meth:`close` explicitly, we recommend you
        use the MSS object as a context manager::

            with mss.mss() as sct:
                ...
        """
        with self._lock:
            if self._closed:
                return
            self._close_impl()
            self._closed = True

    def grab(self, monitor: Monitor | dict[str, int] | tuple[int, int, int, int], /) -> ScreenShot:
        """Retrieve screen pixels for a given monitor.

        Note: ``monitor`` can be a tuple like the one
        :py:meth:`PIL.ImageGrab.grab` accepts: ``(left, top, right, bottom)``

        :param monitor: The coordinates and size of the box to capture.
                        See :meth:`monitors <monitors>` for object details.
        :returns: Screenshot of the requested region.
        """
        from mss.models import Monitor as MonitorCls  # noqa: PLC0415

        # Convert PIL bbox style or dict to Monitor
        if isinstance(monitor, tuple):
            monitor = MonitorCls(
                monitor[0],
                monitor[1],
                monitor[2] - monitor[0],
                monitor[3] - monitor[1],
            )
        elif isinstance(monitor, dict):
            monitor = MonitorCls(
                monitor["left"],
                monitor["top"],
                monitor["width"],
                monitor["height"],
            )

        if monitor["width"] <= 0 or monitor["height"] <= 0:
            msg = f"Region has zero or negative size: {monitor!r}"
            raise ScreenShotError(msg)

        with self._lock:
            screenshot = self._grab_impl(monitor)
            if self.with_cursor and (cursor := self._cursor_impl()):
                return self._merge(screenshot, cursor)
            return screenshot

    @property
    def monitors(self) -> Monitors:
        """Get positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill ``self._monitors`` with all information
        and use it as a cache:

        - ``self._monitors[0]`` is a dict of all monitors together
        - ``self._monitors[N]`` is a dict of the monitor N (with N > 0)

        Each monitor is a dict with:

        - ``left``: the x-coordinate of the upper-left corner
        - ``top``: the y-coordinate of the upper-left corner
        - ``width``: the width
        - ``height``: the height
        """
        with self._lock:
            if not self._monitors:
                self._monitors_impl()
            return self._monitors

    @property
    def primary_monitor(self) -> Monitor | None:
        """Get the primary monitor.

        Returns the monitor marked as primary. If no monitor is marked as primary
        (or the platform doesn't support primary monitor detection), returns the
        first monitor (at index 1). Returns None if no monitors are available.

        .. versionadded:: 10.2.0
        """
        monitors = self.monitors
        if len(monitors) <= 1:  # Only the "all monitors" entry or empty
            return None

        for monitor in monitors[1:]:  # Skip the "all monitors" entry at index 0
            if monitor.is_primary:
                return monitor
        # Fallback to the first monitor if no primary is found
        return monitors[1]

    def save(
        self,
        /,
        *,
        mon: int = 0,
        output: str = "monitor-{mon}.png",
        callback: Callable[[str], None] | None = None,
    ) -> Iterator[str]:
        """Grab a screenshot and save it to a file.

        :param int mon: The monitor to screenshot (default=0). ``-1`` grabs all
            monitors, ``0`` grabs each monitor, and ``N`` grabs monitor ``N``.
        :param str output: The output filename. Keywords: ``{mon}``, ``{top}``,
            ``{left}``, ``{width}``, ``{height}``, ``{date}``.
        :param callable callback: Called before saving the screenshot; receives
            the ``output`` argument.
        :return: Created file(s).
        """
        monitors = self.monitors
        if not monitors:
            msg = "No monitor found."
            raise ScreenShotError(msg)

        if mon == 0:
            # One screenshot by monitor
            for idx, monitor in enumerate(monitors[1:], 1):
                fname = output.format(mon=idx, date=datetime.now(UTC) if "{date" in output else None, **monitor)
                if callable(callback):
                    callback(fname)
                sct = self.grab(monitor)
                to_png(sct.rgb, sct.size, level=self.compression_level, output=fname)
                yield fname
        else:
            # A screenshot of all monitors together or
            # a screenshot of the monitor N.
            mon = 0 if mon == -1 else mon
            try:
                monitor = monitors[mon]
            except IndexError as exc:
                msg = f"Monitor {mon!r} does not exist."
                raise ScreenShotError(msg) from exc

            output = output.format(mon=mon, date=datetime.now(UTC) if "{date" in output else None, **monitor)
            if callable(callback):
                callback(output)
            sct = self.grab(monitor)
            to_png(sct.rgb, sct.size, level=self.compression_level, output=output)
            yield output

    def shot(self, /, **kwargs: Any) -> str:
        """Helper to save the screenshot of the 1st monitor, by default.
        You can pass the same arguments as for :meth:`save`.
        """
        kwargs["mon"] = kwargs.get("mon", 1)
        return next(self.save(**kwargs))

    @staticmethod
    def _merge(screenshot: ScreenShot, cursor: ScreenShot, /) -> ScreenShot:
        """Create composite image by blending screenshot and mouse cursor.

        The cursor image should be in straight (not premultiplied) alpha.
        """
        (cx, cy), (cw, ch) = cursor.pos, cursor.size
        (x, y), (w, h) = screenshot.pos, screenshot.size

        cx2, cy2 = cx + cw, cy + ch
        x2, y2 = x + w, y + h

        overlap = cx < x2 and cx2 > x and cy < y2 and cy2 > y
        if not overlap:
            return screenshot

        screen_raw = screenshot.raw
        cursor_raw = cursor.raw

        cy, cy2 = (cy - y) * 4, (cy2 - y2) * 4
        cx, cx2 = (cx - x) * 4, (cx2 - x2) * 4
        start_count_y = -cy if cy < 0 else 0
        start_count_x = -cx if cx < 0 else 0
        stop_count_y = ch * 4 - max(cy2, 0)
        stop_count_x = cw * 4 - max(cx2, 0)
        rgb = range(3)

        for count_y in range(start_count_y, stop_count_y, 4):
            pos_s = (count_y + cy) * w + cx
            pos_c = count_y * cw

            for count_x in range(start_count_x, stop_count_x, 4):
                spos = pos_s + count_x
                cpos = pos_c + count_x
                alpha = cursor_raw[cpos + 3]

                if not alpha:
                    continue

                if alpha == OPAQUE:
                    screen_raw[spos : spos + 3] = cursor_raw[cpos : cpos + 3]
                else:
                    alpha2 = alpha / 255
                    for i in rgb:
                        screen_raw[spos + i] = int(cursor_raw[cpos + i] * alpha2 + screen_raw[spos + i] * (1 - alpha2))

        return screenshot

    @staticmethod
    def _cfactory(
        attr: Any,
        func: str,
        argtypes: list[Any],
        restype: Any,
        /,
        errcheck: Callable | None = None,
    ) -> None:
        """Factory to create a ctypes function and automatically manage errors."""
        meth = getattr(attr, func)
        meth.argtypes = argtypes
        meth.restype = restype
        if errcheck:
            meth.errcheck = errcheck
