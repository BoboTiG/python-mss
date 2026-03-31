# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

import platform
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Lock
from typing import TYPE_CHECKING, Any

from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot
from mss.tools import to_png

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from mss.linux.xshmgetimage import ShmStatus
    from mss.models import Monitor, Monitors, Size

    # Prior to 3.11, Python didn't have the Self type.  typing_extensions does, but we don't want to depend on it.
    try:
        from typing import Self
    except ImportError:
        try:
            from typing_extensions import Self
        except ImportError:
            Self = Any  # type: ignore[assignment]

try:
    from datetime import UTC
except ImportError:
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


__all__ = ()


class MSSImplementation(ABC):
    """Base class for internal platform/backend implementations.

    Only one of these methods will be called at a time; the containing
    MSS object will hold a lock during these calls.
    """

    __slots__ = ("with_cursor",)

    with_cursor: bool

    def __init__(self, /, *, with_cursor: bool = False) -> None:
        # We put with_cursor on the MSSImplementation because the Xlib
        # backend will turn it off if the library isn't installed.
        # (It's not a separate library under XCB.)  So, we need to let
        # the backend mutate it.

        # We should remove this expectation in 11.0.  It seems
        # unlikely to be practically useful, Xlib is legacy, and just
        # complicates things.
        self.with_cursor = with_cursor

    @abstractmethod
    def cursor(self) -> ScreenShot | None:
        """Retrieve all cursor data. Pixels have to be RGB."""

    @abstractmethod
    def grab(self, monitor: Monitor, /) -> bytearray | tuple[bytearray, Size]:
        """Retrieve all pixels from a monitor. Pixels have to be RGB.

        If the monitor size is not in pixel units, include a Size in
        pixels (see issue #23).
        """

    @abstractmethod
    def monitors(self) -> Monitors:
        """Return positions of monitors."""

    def close(self) -> None:  # noqa: B027 - intentionally empty
        """Clean up.

        This will be called at most once.

        It's not necessary for subclasses to implement this if they
        have nothing to clean up.
        """

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


def _choose_impl(**kwargs: Any) -> MSSImplementation:
    """Return the backend implementation for the current platform.

    Detects the platform we are running on and instantiates the
    appropriate internal implementation class.

    .. seealso::
        - :class:`mss.MSS`
        - :class:`mss.darwin.MSS`
        - :class:`mss.linux.MSS`
        - :class:`mss.windows.MSS`
    """
    os_ = platform.system().lower()

    if os_ == "darwin":
        from mss.darwin import MSSImplDarwin  # noqa: PLC0415

        return MSSImplDarwin(**kwargs)

    if os_ == "linux":
        from mss.linux import choose_impl as choose_impl_linux  # noqa: PLC0415

        # Linux has its own factory to choose the backend.
        return choose_impl_linux(**kwargs)

    if os_ == "windows":
        from mss.windows import MSSImplWindows  # noqa: PLC0415

        return MSSImplWindows(**kwargs)

    msg = f"System {os_!r} not (yet?) implemented."
    raise ScreenShotError(msg)


# Does this belong here?
class MSS:
    """Multiple ScreenShots class

    :param backend: Backend selector, for platforms with multiple backends.
    :param compression_level: PNG compression level.
    :param with_cursor: Include the mouse cursor in screenshots.
    :param display: X11 display name (GNU/Linux only).
    :type display: bytes | str, optional (default :envvar:`$DISPLAY`)
    :param max_displays: Maximum number of displays to enumerate (macOS only).
    :type max_displays: int, optional (default 32)

    .. versionadded:: 8.0.0
        ``compression_level``, ``display``, ``max_displays``, and ``with_cursor`` keyword arguments.
    """

    def __init__(
        self,
        /,
        *,
        backend: str = "default",
        compression_level: int = 6,
        **kwargs: Any,
    ) -> None:
        self._impl: MSSImplementation = _choose_impl(
            backend=backend,
            **kwargs,
        )

        # The cls_image is only used atomically, so does not require locking.
        self.cls_image: type[ScreenShot] = ScreenShot
        # The compression level is only used atomically, so does not require locking.
        #: PNG compression level used when saving the screenshot data into a file
        #: (see :py:func:`zlib.compress()` for details).
        #:
        #: .. versionadded:: 3.2.0
        self.compression_level = compression_level

        # The attributes below are protected by self._lock.  The attributes above are user-visible, so we don't
        # control when they're modified.  Currently, we only make sure that they're safe to modify while locked, or
        # document that the user shouldn't change them.  We could also use properties protect them against changes, or
        # change them under the lock.
        self._lock = Lock()
        self._monitors: Monitors | None = None
        self._closed = False

    def __enter__(self) -> Self:
        """For the cool call `with MSS() as mss:`."""
        return self

    def __exit__(self, *_: object) -> None:
        """For the cool call `with MSS() as mss:`."""
        self.close()

    def close(self) -> None:
        """Clean up.

        This releases resources that MSS may be using.  Once the MSS
        object is closed, it may not be used again.

        It is safe to call this multiple times; multiple calls have no
        effect.

        Rather than use :py:meth:`close` explicitly, we recommend you
        use the MSS object as a context manager::

            with mss.MSS() as sct:
                ...
        """
        with self._lock:
            if self._closed:
                return
            self._impl.close()
            self._closed = True

    def grab(self, monitor: Monitor | tuple[int, int, int, int], /) -> ScreenShot:
        """Retrieve screen pixels for a given monitor.

        Note: ``monitor`` can be a tuple like the one
        :py:meth:`PIL.ImageGrab.grab` accepts: ``(left, top, right, bottom)``

        :param monitor: The coordinates and size of the box to capture.
                        See :meth:`monitors <monitors>` for object details.
        :returns: Screenshot of the requested region.
        """
        # Convert PIL bbox style
        if isinstance(monitor, tuple):
            monitor = {
                "left": monitor[0],
                "top": monitor[1],
                "width": monitor[2] - monitor[0],
                "height": monitor[3] - monitor[1],
            }

        if monitor["width"] <= 0 or monitor["height"] <= 0:
            msg = f"Region has zero or negative size: {monitor!r}"
            raise ScreenShotError(msg)

        with self._lock:
            img_data_and_maybe_size = self._impl.grab(monitor)
            if isinstance(img_data_and_maybe_size, tuple):
                img_data, size = img_data_and_maybe_size
                screenshot = self.cls_image(img_data, monitor, size=size)
            else:
                img_data = img_data_and_maybe_size
                screenshot = self.cls_image(img_data, monitor)
            if self._impl.with_cursor and (cursor := self._impl.cursor()):
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
        - ``is_primary``: (optional) true if this is the primary monitor
        - ``name``: (optional) human-readable device name
        - ``unique_id``: (optional) platform-specific stable identifier for the monitor
        - ``output``: (optional, Linux only) monitor output name, compatible with xrandr
        """
        with self._lock:
            if self._monitors is None:
                self._monitors = self._impl.monitors()
                assert self._monitors is not None  # noqa: S101
            return self._monitors

    @property
    def primary_monitor(self) -> Monitor:
        """Get the primary monitor.

        Returns the monitor marked as primary. If no monitor is marked as primary
        (or the platform doesn't support primary monitor detection), returns the
        first monitor (at index 1).

        :raises ScreenShotError: If no monitors are available.

        .. versionadded:: 10.2.0
        """
        monitors = self.monitors
        if len(monitors) <= 1:  # Only the "all monitors" entry or empty
            msg = "No monitor found."
            raise ScreenShotError(msg)

        return next(
            (
                monitor
                for monitor in monitors[1:]  # Skip the "all monitors" entry at index 0
                if monitor.get("is_primary", False)
            ),
            monitors[1],  # Fallback to the first monitor if no primary is found
        )

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

    # Some backends may expose additional read-only attributes.  Those
    # are implemented here, as properties.  By making them properties,
    # instead of using __getattr__, they're also accessible to Sphinx
    # and type checkers.
    #
    # Important: We need to be judicious in what we add here.  We
    # really don't want these to proliferate.  Some, like
    # max_displays, should probably be removed in 11.0.  with_cursor
    # should probably be moved to MSS instead of MSSImplementation (as
    # noted there).
    #
    # The shm_status is mostly a debugging field, and probably should
    # be replaced with something different.  Ideas include a log
    # message, an exception if the user explicitly requested
    # xshmgetimage, or a platform-independent message attribute (for
    # instance, if Windows has to fall back to GDI).

    @property
    def shm_status(self) -> ShmStatus:
        """Whether we can use the MIT-SHM extensions for this connection.

        Availability: GNU/Linux, when using the default XShmGetImage backend.

        This will not be ``AVAILABLE`` until at least one capture has succeeded.
        It may be set to ``UNAVAILABLE`` sooner.

        .. versionadded:: 10.2.0
        """
        return self._impl.shm_status  # type: ignore[attr-defined]

    @property
    def shm_fallback_reason(self) -> str | None:
        """If MIT-SHM is unavailable, the reason why (for debugging purposes).

        Availability: GNU/Linux, when using the default XShmGetImage backend.

        .. versionadded:: 10.2.0
        """
        return self._impl.shm_fallback_reason  # type: ignore[attr-defined]

    @property
    def max_displays(self) -> int:
        """Maximum number of displays to handle.

        Availability: macOS

        .. versionadded:: 8.0.0
        """
        return self._impl.max_displays  # type: ignore[attr-defined]

    @property
    def with_cursor(self) -> bool:
        """Include the mouse cursor in screenshots.

        In some circumstances, it may not be possible to include the
        cursor.  In that case, MSS will automatically change this to
        False when the object is created.

        This cannot be changed after creating the object.

        .. versionadded:: 8.0.0
        """
        return self._impl.with_cursor


# TODO(jholveck): #493 Remove compatibility alias after 10.x transition period.
MSSBase = MSS
