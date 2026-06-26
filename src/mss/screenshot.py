# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from mss.exception import ScreenShotError
from mss.models import Monitor, Pixel, Pixels, Pos, Size

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    from typing_extensions import Buffer


class ScreenShot:
    """Screenshot object.

    .. note::
        A better name would have been *Image*, but to prevent collisions
        with PIL.Image, it has been decided to use *ScreenShot*.
    """

    __slots__ = {"__bgra", "__pixels", "__rgb", "_raw", "pos", "size"}

    def __init__(self, data: Buffer, monitor: Monitor, /, *, size: Size | None = None) -> None:
        self.__pixels: Pixels | None = None
        self.__rgb: memoryview | None = None

        #: NamedTuple of the screenshot coordinates.
        self.pos: Pos = Pos(monitor["left"], monitor["top"])

        #: NamedTuple of the screenshot size.
        self.size: Size = Size(monitor["width"], monitor["height"]) if size is None else size

        # Buffer of the raw BGRA pixels, retrieved by the platform-specific implementations.  This is kept read-write if
        # it was originally so, in order for _merge to work, and so it can be used with ctypes.  However, it should not
        # be modified once __pixels or __rgb have been accessed, so that the cached values for __pixels and __rgb aren't
        # potentially inconsistent if the user changes data.
        self._raw: memoryview = memoryview(data)
        assert self._raw.nbytes == self.size.width * self.size.height * 4, (  # noqa: S101
            "Data size does not match screenshot dimensions."
        )
        assert self._raw.format == "B", "Data format is not bytes."  # noqa: S101

    def __repr__(self) -> str:
        return f"<{type(self).__name__} pos={self.left},{self.top} size={self.width}x{self.height}>"

    @property
    def __array_interface__(self) -> dict[str, Any]:
        """NumPy array interface support.

        This is used by NumPy, many SciPy projects, CuPy, PyTorch (via
        :py:func:`torch.from_numpy`), TensorFlow (via
        :py:func:`tf.convert_to_tensor`), JAX (via
        :py:func:`jax.numpy.asarray`), Pandas, scikit-learn, Matplotlib,
        some OpenCV functions, and others.  This allows you to pass a
        :class:`ScreenShot` instance directly to these libraries without
        needing to convert it first.

        This is in HWC order, with 4 channels (BGRA).

        The array is read-write, for maximum compatibility.  However,
        actually modifying the data may cause undefined behavior.

        .. seealso::

            https://numpy.org/doc/stable/reference/arrays.interface.html
               The NumPy array interface protocol specification
        """
        return {
            "version": 3,
            "shape": (self.height, self.width, 4),
            "typestr": "|u1",
            "data": self._raw,
        }

    @classmethod
    def from_size(cls: type[ScreenShot], data: Buffer, width: int, height: int, /) -> ScreenShot:
        """Instantiate a new class given only screenshot's data and size."""
        monitor = {"left": 0, "top": 0, "width": width, "height": height}
        return cls(data, monitor)

    @property
    def bgra(self) -> memoryview:
        """BGRx values from the BGRx raw pixels.

        The format is a memoryview object of bytes.  These are in a
        BGRxBGRx... sequence.  A specific pixel can be accessed as
        ``bgra[(y * width + x) * 4:(y * width + x) * 4 + 4].``

        The memoryview is read-write, for compatibility with ctypes'
        :py:func:`from_buffer`.  However, actually modifying the data
        may cause undefined behavior.

        .. note::
            While the name is ``bgra``, the alpha channel may or may
            not be valid.

        .. version-changed:: 11.0.0
            Prior to this version, this was a :py:class:`bytes` object.
            It was changed to a memoryview for improved performance.
            Most practical uses are unaffected by this change, as
            ``memoryview`` supports most of the same operations as
            ``bytes``.  If needed, you can use
            :py:meth:`memoryview.tobytes` to get a ``bytes`` object.
        """
        return self._raw

    @property
    def raw(self) -> memoryview:
        """Deprecated alias for :py:attr:`bgra`.

        .. version-deprecated:: 10.2.0
            Use :py:attr:`bgra` instead.  This alias will be removed in
            a future version.

        .. version-changed:: 11.0.0
            Prior to this version, this was a :py:class:`bytearray`.
            This :py:attr:`raw` alias is retained, although as a
            :py:class:`memoryview`, for backwards compatibility: most
            existing uses are not affected, as ``memoryview`` supports
            most of the same operations as ``bytearray``.  If needed,
            you can use ``bytearray(raw)`` to get a ``bytearray``
            object.
        """
        warnings.warn("The raw property is deprecated.  Use bgra instead.", DeprecationWarning, stacklevel=2)
        return self._raw

    @property
    def pixels(self) -> Pixels:
        """RGB tuples.

        The format is a list of rows.  Each row is a list of pixels.
        Each pixel is a tuple of (R, G, B).
        """
        if self.__pixels is None:
            rgb_tuples: Iterator[Pixel] = zip(self._raw[2::4], self._raw[1::4], self._raw[::4], strict=False)
            self.__pixels = list(zip(*[iter(rgb_tuples)] * self.width, strict=False))

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
    def rgb(self) -> memoryview:
        """Compute RGB values from the BGRA raw pixels.

        The format is a memoryview object of bytes.  These are in a
        RGBRGB... sequence.  A specific pixel can be accessed as
        ``rgb[(y * width + x) * 3:(y * width + x) * 3 + 3].``

        The memoryview is read-write, for compatibility with ctypes'
        :py:func:`from_buffer`.  However, actually modifying the data
        may cause undefined behavior.

        .. note::
            This is a computed property.  If possible, using the
            :py:attr:`bgra` property directly is usually more efficient.

        .. version-changed:: 11.0.0
            Prior to this version, this was a :py:class:`bytes` object.
            It was changed to a memoryview for improved performance.
            Most practical uses are unaffected by this change, as
            ``memoryview`` supports most of the same operations as
            ``bytes``.  If needed, you can use
            :py:meth:`memoryview.tobytes` to get a ``bytes`` object.
        """
        if self.__rgb is None:
            rgb = bytearray(self.height * self.width * 3)
            raw = self._raw
            rgb[::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[::4]
            # We could just return the bytearray directly.  However, we would rather give ourselves the flexibility to
            # use other buffer types in the future.  Rather than declaring our return type as just generically Buffer
            # (which doesn't guarantee the indexing behavior of memoryview), we always return a memoryview, which is
            # cheap.
            self.__rgb = memoryview(rgb)

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
