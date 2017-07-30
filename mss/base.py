# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from .exception import ScreenShotError
from .screenshot import ScreenShot
from .tools import to_png


class MSSBase(object):
    """ This class will be overloaded by a system specific one. """

    cls_image = ScreenShot  # type: object
    _monitors = []  # type: List[Dict[str, int]]

    def __enter__(self):
        # type: () -> MSSBase
        """ For the cool call `with MSS() as mss:`. """

        return self

    def __exit__(self, *_):
        # type: (*str) -> None
        """ For the cool call `with MSS() as mss:`. """

    def grab(self, monitor):
        # type: (Dict[str, int]) -> ScreenShot
        """
        Retrieve screen pixels for a given monitor.

        :param monitor: The coordinates and size of the box to capture.
                        See :meth:`monitors <monitors>` for object details.
        :return :class:`ScreenShot <ScreenShot>`.
        """

        raise NotImplementedError('Subclasses need to implement this!')

    @property
    def monitors(self):
        # type: () -> List[Dict[str, int]]
        """
        Get positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill self._monitors with all informations
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

        raise NotImplementedError('Subclasses need to implement this!')

    def save(self, mon=0, output='monitor-%d.png', callback=None):
        # type: (int, str, Callable[[str], None]) -> Iterator[str]
        """
        Grab a screenshot and save it to a file.

        :param int mon: The monitor to screenshot (default=0).
                        -1: grab one screenshot of all monitors
                         0: grab one screenshot by monitor
                        N: grab the screenshot of the monitor N

        :param str output: The output filename.
                           %d, if present, will be replaced by
                           the monitor number.

        :param callable callback: Callback called before saving
                                  the screenshot to a file.
                                  Take the ``output`` argument as parameter.

        :return generator: Created file(s).
        """

        monitors = self.monitors
        if not monitors:
            raise ScreenShotError('No monitor found.')

        if mon == 0:
            # One screenshot by monitor
            for i, monitor in enumerate(monitors[1:], 1):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i))
                if callable(callback):
                    callback(fname)
                sct = self.grab(monitor)
                to_png(sct.rgb, sct.size, fname)
                yield fname
        else:
            # A screenshot of all monitors together or
            # a screenshot of the monitor N.
            mon_number = 0 if mon == -1 else mon
            try:
                monitor = monitors[mon_number]
            except IndexError:
                raise ScreenShotError('Monitor does not exist.', locals())

            if '%d' in output:
                output = output.replace('%d', str(mon_number))
            if callable(callback):
                callback(output)
            sct = self.grab(monitor)
            to_png(sct.rgb, sct.size, output)
            yield output

    def shot(self, **kwargs):
        """
        Helper to save the screenshot of the 1st monitor, by default.
        You can pass the same arguments as for ``save``.
        """

        kwargs['mon'] = kwargs.get('mon', 1)
        return next(self.save(**kwargs))
