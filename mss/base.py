"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING
from threading import Lock

from .exception import ScreenShotError
from .screenshot import ScreenShot
from .tools import to_png

if TYPE_CHECKING:
    # pylint: disable=ungrouped-imports
    from typing import Any, Callable, Iterator, List, Optional, Type  # noqa

    from .models import Monitor, Monitors  # noqa


lock = Lock()


class MSSBase(metaclass=ABCMeta):
    """ This class will be overloaded by a system specific one. """

    __slots__ = {"_monitors", "cls_image", "compression_level"}

    def __init__(self):
        self.cls_image = ScreenShot  # type: Type[ScreenShot]
        self.compression_level = 6
        self._monitors = []  # type: Monitors

    def __enter__(self):
        # type: () -> MSSBase
        """ For the cool call `with MSS() as mss:`. """

        return self

    def __exit__(self, *_):
        """ For the cool call `with MSS() as mss:`. """

        self.close()

    @abstractmethod
    def _grab_impl(self, monitor):
        # type: (Monitor) -> ScreenShot
        """
        Retrieve all pixels from a monitor. Pixels have to be RGB.
        That method has to be run using a threading lock.
        """

    @abstractmethod
    def _monitors_impl(self):
        # type: () -> None
        """
        Get positions of monitors (has to be run using a threading lock).
        It must populate self._monitors.
        """

    def close(self):
        # type: () -> None
        """ Clean-up. """

    def grab(self, monitor, with_cursor=False):
        # type: (Monitor, Optional[bool]) -> ScreenShot
        """
        Retrieve screen pixels for a given monitor.

        Note: *monitor* can be a tuple like PIL.Image.grab() accepts.

        :param monitor: The coordinates and size of the box to capture.
                        See :meth:`monitors <monitors>` for object details.

        :param bool with_cursor: include mouse cursor in capture or not.
                        See :meth:`monitors <monitors>` for object details.

        :return :class:`ScreenShot <ScreenShot>`.
        """

        # Convert PIL bbox style
        if isinstance(monitor, tuple):
            monitor = {
                "left": monitor[0],
                "top": monitor[1],
                "width": monitor[2] - monitor[0],
                "height": monitor[3] - monitor[1],
            }

        with lock:
            screenshot = self._grab_impl(monitor)
            if with_cursor:
                try:
                    return self.draw(
                        screenshot, self._cursor_impl()
                    )
                except NotImplementedError:
                    return screenshot
            else:
                return screenshot

    @property
    def monitors(self):
        # type: () -> Monitors
        """
        Get positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill self._monitors with all information
        and use it as a cache:
            self._monitors[0] is a dict of all monitors together
            self._monitors[N] is a dict of the monitor N (with N > 0)

        Each monitor is a dict with:
        {
            'left':   the x-coordinate of the upper-left corner,
            'top':    the y-coordinate of the upper-left corner,
            'width':  the width,
            'height': the height
        }
        """

        if not self._monitors:
            with lock:
                self._monitors_impl()

        return self._monitors

    def save(self, mon=0, output="monitor-{mon}.png", callback=None):
        # type: (int, str, Callable[[str], None]) -> Iterator[str]
        """
        Grab a screen shot and save it to a file.

        :param int mon: The monitor to screen shot (default=0).
                        -1: grab one screen shot of all monitors
                         0: grab one screen shot by monitor
                        N: grab the screen shot of the monitor N

        :param str output: The output filename.

            It can take several keywords to customize the filename:
            - `{mon}`: the monitor number
            - `{top}`: the screen shot y-coordinate of the upper-left corner
            - `{left}`: the screen shot x-coordinate of the upper-left corner
            - `{width}`: the screen shot's width
            - `{height}`: the screen shot's height
            - `{date}`: the current date using the default formatter

            As it is using the `format()` function, you can specify
            formatting options like `{date:%Y-%m-%s}`.

        :param callable callback: Callback called before saving the
            screen shot to a file.  Take the `output` argument as parameter.

        :return generator: Created file(s).
        """

        monitors = self.monitors
        if not monitors:
            raise ScreenShotError("No monitor found.")

        if mon == 0:
            # One screen shot by monitor
            for idx, monitor in enumerate(monitors[1:], 1):
                fname = output.format(mon=idx, date=datetime.now(), **monitor)
                if callable(callback):
                    callback(fname)
                sct = self.grab(monitor)
                to_png(sct.rgb, sct.size, level=self.compression_level, output=fname)
                yield fname
        else:
            # A screen shot of all monitors together or
            # a screen shot of the monitor N.
            mon = 0 if mon == -1 else mon
            try:
                monitor = monitors[mon]
            except IndexError:
                # pylint: disable=raise-missing-from
                raise ScreenShotError("Monitor {!r} does not exist.".format(mon))

            output = output.format(mon=mon, date=datetime.now(), **monitor)
            if callable(callback):
                callback(output)
            sct = self.grab(monitor)
            to_png(sct.rgb, sct.size, level=self.compression_level, output=output)
            yield output

    def shot(self, **kwargs):
        # type: (Any) -> str
        """
        Helper to save the screen shot of the 1st monitor, by default.
        You can pass the same arguments as for ``save``.
        """

        kwargs["mon"] = kwargs.get("mon", 1)
        return next(self.save(**kwargs))

    @staticmethod
    def _cfactory(attr, func, argtypes, restype, errcheck=None):
        # type: (Any, str, List[Any], Any, Optional[Callable]) -> None
        """ Factory to create a ctypes function and automatically manage errors. """

        meth = getattr(attr, func)
        meth.argtypes = argtypes
        meth.restype = restype
        if errcheck:
            meth.errcheck = errcheck

    @staticmethod
    def draw(background, foreground):
        # type: (ScreenShot, ScreenShot) -> ScreenShot
        """ Create composite image by blending screenshot and mouse cursor. """

        (cx, cy), (cw, ch) = foreground.pos, foreground.size
        (x, y), (w, h) = background.pos, background.size

        cx2, cy2 = cx + cw, cy + ch
        x2, y2 = x + w, y + h

        overlap = (cx < x2 and cx2 > x and
                   cy < y2 and cy2 > y)

        if not overlap:
            return background

        screen = background.raw
        cursor = foreground.raw
        rgb = range(3)

        cy, cy2 = (cy - y) * 4, (cy2 - y2) * 4
        cx, cx2 = (cx - x) * 4, (cx2 - x2) * 4

        startCountY = - cy if cy < 0 else 0
        startCountX = - cx if cx < 0 else 0

        stopCountY = ch * 4 - (cy2 if cy2 > 0 else 0)
        stopCountX = cw * 4 - (cx2 if cx2 > 0 else 0)

        Yrange = range(startCountY, stopCountY, 4)
        Xrange = range(startCountX, stopCountX, 4)

        for countY in Yrange:

            sPos = (countY + cy) * w + cx
            cPos = countY * cw

            for countX in Xrange:

                spos = sPos + countX
                cpos = cPos + countX
                alpha = cursor[cpos + 3]

                if not alpha:
                    continue

                elif alpha == 255:
                    screen[spos:spos + 3] = cursor[cpos:cpos + 3]

                else:
                    alpha = alpha / 255
                    for i in rgb:
                        screen[spos + i] = int(
                            cursor[cpos + i] * alpha +
                            screen[spos + i] * (1 - alpha)
                        )

        return background
