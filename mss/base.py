# coding: utf-8
"""
mss.base
~~~~~~~~

This module contains the basic classes that power MSS.

.. note::

    The :class:`MSSBase <MSSBase>` class must be the parent class
    for every OS speicific implementation.
"""

import collections

from .exception import ScreenShotError
from .tools import to_png


class MSSBase(object):
    """ This class will be overloaded by a system specific one. """

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

        mon (integer, default: 0)
            -1: grab one screenshot of all monitors
             0: grab one screenshot by monitor
             N: grab the screenshot of the monitor N

        output (string, default: monitor-%d.png)
            The output filename.
            %d, if present, will be replaced by the monitor number.

        callback (method)
            Callback called before saving the screenshot to a file.
            Take the 'output' argument as parameter.

        This is a generator which returns created files.
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


class ScreenShot(object):
    """
    Screen shot object.

    .. note::

        A better name would be "Image", but to prevent collisions
        with PIL.Image, it has been decided to use another name.
    """

    __pixels = None  # type: List[Tuple[int, int, int]]
    __rgb = None  # type: bytes

    def __init__(self, data, monitor):
        # type: (bytearray, Dict[str, int]) -> None
        #: Bytearray of the raw BGRA pixels retrieved by ctype
        #: OS independent implementations.
        self.raw = bytearray(data)  # type: bytearray

        #: NamedTuple of the screen shot coordinates.
        self.pos = collections.namedtuple('pos', 'left, top')(
            monitor['left'], monitor['top'])  # type: Any

        #: NamedTuple of the screen shot size.
        self.size = collections.namedtuple('size', 'width, height')(
            monitor['width'], monitor['height'])  # type: Any

    def __repr__(self):
        # type: () -> str
        return ('<{!s}'
                ' pos={cls.left},{cls.top}'
                ' size={cls.width}x{cls.height}'
                '>').format(type(self).__name__, cls=self)

    @property
    def __array_interface__(self):
        # type: () -> dict[str, Any]
        """
        Numpy array interface support.
        It uses raw data in BGRA form.

        See https://docs.scipy.org/doc/numpy/reference/arrays.interface.html
        """

        return dict(version=3,
                    shape=(self.height, self.width, 4),
                    typestr='|u1',
                    data=self.raw)

    @classmethod
    def from_size(cls, data, width, height):
        # type: (bytearray, int, int) -> ScreenShot
        """ Instanciate a new class given only screenshot's data and size. """

        monitor = {'left': 0, 'top': 0, 'width': width, 'height': height}
        return cls(data, monitor)

    @property
    def top(self):
        # type: () -> int
        """ Conveniant accessor to the top position. """
        return self.pos.top

    @property
    def left(self):
        # type: () -> int
        """ Conveniant accessor to the left position. """
        return self.pos.left

    @property
    def width(self):
        # type: () -> int
        """ Conveniant accessor to the width size. """
        return self.size.width

    @property
    def height(self):
        # type: () -> int
        """ Conveniant accessor to the height size. """
        return self.size.height

    @property
    def pixels(self):
        # type: () -> List[Tuple[int, int, int]]
        """
        :return list: RGB tuples.
        """

        if not self.__pixels:
            rgb_tuples = zip(self.raw[2::4], self.raw[1::4], self.raw[0::4])
            self.__pixels = list(zip(*[iter(rgb_tuples)] * self.width))

        return self.__pixels

    def pixel(self, coord_x, coord_y):
        # type: (int, int) -> Tuple[int, int, int]
        """
        Returns the pixel value at a given position.

        : param coord_x int: The x coordinate.
        : param coord_y int: The y coordinate.
        :return tuple: The pixel value as (R, G, B).
        """

        try:
            return self.pixels[coord_y][coord_x]
        except IndexError:
            raise ScreenShotError('Pixel location out of range.', locals())

    @property
    def rgb(self):
        # type: () -> bytes
        """
        Compute RGB values from the BGRA raw pixels.

        :return bytes: RGB pixels.
        """

        if not self.__rgb:
            self.__rgb = bytearray(self.height * self.width * 3)
            self.__rgb[0::3], self.__rgb[1::3], self.__rgb[2::3] = \
                self.raw[2::4], self.raw[1::4], self.raw[0::4]
            self.__rgb = bytes(self.__rgb)

        return self.__rgb
