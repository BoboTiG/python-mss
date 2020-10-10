"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from typing import TYPE_CHECKING

from .models import Size, Pos
from .exception import ScreenShotError

if TYPE_CHECKING:
    from typing import Any, Dict, Iterator, Optional  # noqa

    from .models import Monitor, Pixel, Pixels  # noqa


class ScreenShot:
    """
    Screen shot object.

    .. note::

        A better name would have  been *Image*, but to prevent collisions
        with PIL.Image, it has been decided to use *ScreenShot*.
    """

    __slots__ = {"__pixels", "__rgb", "pos", "raw", "size"}

    def __init__(self, data, monitor, size=None):
        # type: (bytearray, Monitor, Optional[Size]) -> None

        self.__pixels = None  # type: Optional[Pixels]
        self.__rgb = None  # type: Optional[bytes]

        #: Bytearray of the raw BGRA pixels retrieved by ctypes
        #: OS independent implementations.
        self.raw = data

        #: NamedTuple of the screen shot coordinates.
        self.pos = Pos(monitor["left"], monitor["top"])

        if size is not None:
            #: NamedTuple of the screen shot size.
            self.size = size
        else:
            self.size = Size(monitor["width"], monitor["height"])

    def __repr__(self):
        return ("<{!s} pos={cls.left},{cls.top} size={cls.width}x{cls.height}>").format(
            type(self).__name__, cls=self
        )

    @property
    def __array_interface__(self):
        # type: () -> Dict[str, Any]
        """
        Numpy array interface support.
        It uses raw data in BGRA form.

        See https://docs.scipy.org/doc/numpy/reference/arrays.interface.html
        """

        return {
            "version": 3,
            "shape": (self.height, self.width, 4),
            "typestr": "|u1",
            "data": self.raw,
        }

    @classmethod
    def from_size(cls, data, width, height):
        # type: (bytearray, int, int) -> ScreenShot
        """ Instantiate a new class given only screen shot's data and size. """

        monitor = {"left": 0, "top": 0, "width": width, "height": height}
        return cls(data, monitor)

    @property
    def bgra(self):
        # type: () -> bytes
        """ BGRA values from the BGRA raw pixels. """
        return bytes(self.raw)

    @property
    def height(self):
        # type: () -> int
        """ Convenient accessor to the height size. """
        return self.size.height

    @property
    def left(self):
        # type: () -> int
        """ Convenient accessor to the left position. """
        return self.pos.left

    @property
    def pixels(self):
        # type: () -> Pixels
        """
        :return list: RGB tuples.
        """

        if not self.__pixels:
            rgb_tuples = zip(
                self.raw[2::4], self.raw[1::4], self.raw[0::4]
            )  # type: Iterator[Pixel]
            self.__pixels = list(zip(*[iter(rgb_tuples)] * self.width))  # type: ignore

        return self.__pixels

    @property
    def rgb(self):
        # type: () -> bytes
        """
        Compute RGB values from the BGRA raw pixels.

        :return bytes: RGB pixels.
        """

        if not self.__rgb:
            rgb = bytearray(self.height * self.width * 3)
            raw = self.raw
            rgb[0::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[0::4]
            self.__rgb = bytes(rgb)

        return self.__rgb

    @property
    def top(self):
        # type: () -> int
        """ Convenient accessor to the top position. """
        return self.pos.top

    @property
    def width(self):
        # type: () -> int
        """ Convenient accessor to the width size. """
        return self.size.width

    def pixel(self, coord_x, coord_y):
        # type: (int, int) -> Pixel
        """
        Returns the pixel value at a given position.

        :param int coord_x: The x coordinate.
        :param int coord_y: The y coordinate.
        :return tuple: The pixel value as (R, G, B).
        """

        try:
            return self.pixels[coord_y][coord_x]  # type: ignore
        except IndexError:
            # pylint: disable=raise-missing-from
            raise ScreenShotError(
                "Pixel location ({}, {}) is out of range.".format(coord_x, coord_y)
            )
