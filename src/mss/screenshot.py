# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mss.exception import ScreenShotError
from mss.models import Monitor, Pixel, Pixels, Pos, Size

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Iterator


class ScreenShot:
    """Screenshot object.

    .. note::

        A better name would have  been *Image*, but to prevent collisions
        with PIL.Image, it has been decided to use *ScreenShot*.
    """

    __slots__ = {"__pixels", "__rgb", "pos", "raw", "size"}

    def __init__(self, data: bytearray, monitor: Monitor, /, *, size: Size | None = None) -> None:
        self.__pixels: Pixels | None = None
        self.__rgb: bytes | None = None

        #: Bytearray of the raw BGRA pixels retrieved by ctypes
        #: OS independent implementations.
        self.raw: bytearray = data

        #: NamedTuple of the screenshot coordinates.
        self.pos: Pos = Pos(monitor["left"], monitor["top"])

        #: NamedTuple of the screenshot size.
        self.size: Size = Size(monitor["width"], monitor["height"]) if size is None else size

    def __repr__(self) -> str:
        return f"<{type(self).__name__} pos={self.left},{self.top} size={self.width}x{self.height}>"

    @property
    def __array_interface__(self) -> dict[str, Any]:
        """NumPy array interface support.

        This is used by NumPy, many SciPy projects, CuPy, PyTorch (via
        ``torch.from_numpy``), TensorFlow (via ``tf.convert_to_tensor``),
        JAX (via ``jax.numpy.asarray``), Pandas, scikit-learn, Matplotlib,
        some OpenCV functions, and others.  This allows you to pass a
        :class:`ScreenShot` instance directly to these libraries without
        needing to convert it first.

        This is in HWC order, with 4 channels (BGRA).

        .. seealso::

            https://numpy.org/doc/stable/reference/arrays.interface.html
               The NumPy array interface protocol specification
        """
        return {
            "version": 3,
            "shape": (self.height, self.width, 4),
            "typestr": "|u1",
            "data": self.raw,
        }

    @classmethod
    def from_size(cls: type[ScreenShot], data: bytearray, width: int, height: int, /) -> ScreenShot:
        """Instantiate a new class given only screenshot's data and size."""
        monitor = {"left": 0, "top": 0, "width": width, "height": height}
        return cls(data, monitor)

    @property
    def bgra(self) -> bytes:
        """BGRx values from the BGRx raw pixels.

        The format is a bytes object with BGRxBGRx... sequence.  A specific
        pixel can be accessed as bgra[(y * width + x) * 4:(y * width + x) * 4 + 4].

        .. note::
            While the name is `bgra`, the alpha channel may or may not be valid.
        """
        return bytes(self.raw)

    @property
    def pixels(self) -> Pixels:
        """RGB tuples.

        The format is a list of rows.  Each row is a list of pixels.
        Each pixel is a tuple of (R, G, B).
        """
        if not self.__pixels:
            rgb_tuples: Iterator[Pixel] = zip(self.raw[2::4], self.raw[1::4], self.raw[::4])
            self.__pixels = list(zip(*[iter(rgb_tuples)] * self.width))

        return self.__pixels

    def pixel(self, coord_x: int, coord_y: int) -> Pixel:
        """Return the pixel value at a given position.

        :returns: A tuple of (R, G, B) values.
        """
        try:
            return self.pixels[coord_y][coord_x]
        except IndexError as exc:
            msg = f"Pixel location ({coord_x}, {coord_y}) is out of range."
            raise ScreenShotError(msg) from exc

    @property
    def rgb(self) -> bytes:
        """Compute RGB values from the BGRA raw pixels.

        The format is a bytes object with BGRBGR... sequence.  A specific
        pixel can be accessed as rgb[(y * width + x) * 3:(y * width + x) * 3 + 3].
        """
        if not self.__rgb:
            rgb = bytearray(self.height * self.width * 3)
            raw = self.raw
            rgb[::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[::4]
            self.__rgb = bytes(rgb)

        return self.__rgb

    @property
    def top(self) -> int:
        """Convenient accessor to the top position."""
        return self.pos.top

    @property
    def left(self) -> int:
        """Convenient accessor to the left position."""
        return self.pos.left

    @property
    def width(self) -> int:
        """Convenient accessor to the width size."""
        return self.size.width

    @property
    def height(self) -> int:
        """Convenient accessor to the height size."""
        return self.size.height
