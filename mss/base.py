"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
from abc import ABCMeta, abstractmethod
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Iterator, List, Optional, Tuple, Type, Union

from .exception import ScreenShotError
from .models import Monitor, Monitors
from .screenshot import ScreenShot
from .tools import to_png

lock = Lock()


class MSSBase(metaclass=ABCMeta):
    """This class will be overloaded by a system specific one."""

    __slots__ = {"_monitors", "cls_image", "compression_level"}

    def __init__(self) -> None:
        self.cls_image: Type[ScreenShot] = ScreenShot
        self.compression_level = 6
        self._monitors: Monitors = []

    def __enter__(self) -> "MSSBase":
        """For the cool call `with MSS() as mss:`."""

        return self

    def __exit__(self, *_: Any) -> None:
        """For the cool call `with MSS() as mss:`."""

        self.close()

    @abstractmethod
    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """
        Retrieve all pixels from a monitor. Pixels have to be RGB.
        That method has to be run using a threading lock.
        """

    @abstractmethod
    def _monitors_impl(self) -> None:
        """
        Get positions of monitors (has to be run using a threading lock).
        It must populate self._monitors.
        """

    def close(self) -> None:
        """Clean-up."""

    def grab(self, monitor: Union[Monitor, Tuple[int, int, int, int]]) -> ScreenShot:
        """
        Retrieve screen pixels for a given monitor.

        Note: *monitor* can be a tuple like the one PIL.Image.grab() accepts.

        :param monitor: The coordinates and size of the box to capture.
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
            return self._grab_impl(monitor)

    @property
    def monitors(self) -> Monitors:
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

    def save(
        self,
        mon: int = 0,
        output: str = "monitor-{mon}.png",
        callback: Callable[[str], None] = None,
    ) -> Iterator[str]:
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
                raise ScreenShotError(f"Monitor {mon!r} does not exist.")

            output = output.format(mon=mon, date=datetime.now(), **monitor)
            if callable(callback):
                callback(output)
            sct = self.grab(monitor)
            to_png(sct.rgb, sct.size, level=self.compression_level, output=output)
            yield output

    def shot(self, **kwargs: Any) -> str:
        """
        Helper to save the screen shot of the 1st monitor, by default.
        You can pass the same arguments as for ``save``.
        """

        kwargs["mon"] = kwargs.get("mon", 1)
        return next(self.save(**kwargs))

    @staticmethod
    def _cfactory(
        attr: Any,
        func: str,
        argtypes: List[Any],
        restype: Any,
        errcheck: Optional[Callable] = None,
    ) -> None:
        """Factory to create a ctypes function and automatically manage errors."""

        meth = getattr(attr, func)
        meth.argtypes = argtypes
        meth.restype = restype
        if errcheck:
            meth.errcheck = errcheck
