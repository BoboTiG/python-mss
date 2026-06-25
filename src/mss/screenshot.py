# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from mss.exception import ScreenShotError
from mss.models import Monitor, Pixel, Pixels, Pos, Size

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    import numpy as np
    import PIL.Image
    import tensorflow as tf
    import torch
    from typing_extensions import Buffer

Channels = Literal["BGRA", "BGR", "RGB", "RGBA"]
Layout = Literal["HWC", "CHW"]


class ScreenShot:
    """Screenshot object.

    .. note::
        A better name would have been *Image*, but to prevent collisions
        with PIL.Image, it has been decided to use *ScreenShot*.
    """

    __slots__ = {"__bgra", "__pixels", "__rgb", "_raw", "pos", "size"}

    def __init__(self, data: Buffer, monitor: Monitor, /, *, size: Size | None = None) -> None:
        self.__bgra: memoryview | None = None
        self.__pixels: Pixels | None = None
        self.__rgb: memoryview | None = None

        #: NamedTuple of the screenshot coordinates.
        self.pos: Pos = Pos(monitor["left"], monitor["top"])

        #: NamedTuple of the screenshot size.
        self.size: Size = Size(monitor["width"], monitor["height"]) if size is None else size

        # Buffer of the raw BGRA pixels, retrieved by the
        # platform-specific implementations.  This is kept read-write
        # if it was originally so, in order for _merge to work.
        # However, it should be made read-only before returning to the
        # user (via bgra), so that the cached values for __pixels and
        # __rgb aren't potentially inconsistent if the user changes
        # data.
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
        ``torch.from_numpy``), TensorFlow (via ``tf.convert_to_tensor``),
        JAX (via ``jax.numpy.asarray``), Pandas, scikit-learn, Matplotlib,
        some OpenCV functions, and others.  This allows you to pass a
        :py:class:`ScreenShot` instance directly to these libraries without
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
            "data": self.bgra,
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

        The memoryview is read-only.  PyTorch will issue a warning
        when given a read-only buffer, but will still work.  However,
        actually modifying the data may cause undefined behavior.

        While the name is ``bgra``, the alpha channel may not represent
        meaningful transparency on all platforms/backends.
        """
        # Making a read-only copy of a memoryview is very cheap.  But
        # we still always return the same memoryview: somebody using a
        # property may expect it to be identical (under the `is`
        # operator) every time.
        if self.__bgra is None:
            self.__bgra = self._raw.toreadonly()
        return self.__bgra

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
        ``rgb[(y * width + x) * 4:(y * width + x) * 4 + 4].``

        The memoryview is read-only.  PyTorch will issue a warning
        when given a read-only buffer, but will still work.  However,
        actually modifying the data may cause undefined behavior.

        .. note::
            This is a computed property.  If possible, using the
            :py:attr:`bgra` property directly is usually more
            efficient.
        """
        if self.__rgb is None:
            rgb = bytearray(self.height * self.width * 3)
            raw = self._raw
            rgb[::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[::4]
            self.__rgb = memoryview(rgb).toreadonly()

        return self.__rgb

    def to_pil(self, mode: str = "RGB") -> PIL.Image.Image:
        """Convert the screenshot to a Pillow image.

        :param mode: The requested image mode.  Must be ``"RGB"``
            (default) or ``"RGBA"``.

        When requesting ``"RGBA"``, the alpha channel may not represent
        meaningful transparency on all platforms/backends.

        TODO(jholveck): After #536 is resolved, add a note about the
        buffer sharing semantics.
        """
        mode = mode.upper()
        if mode not in {"RGB", "RGBA"}:
            msg = "Mode must be 'RGB' or 'RGBA'"
            raise ValueError(msg)

        from PIL import Image  # noqa: PLC0415

        raw_mode = "BGRX" if mode == "RGB" else "BGRA"
        return Image.frombuffer(mode, self.size, self._raw, "raw", raw_mode, 0, 1)

    def to_numpy(self, channels: Channels = "RGB", layout: Layout = "HWC") -> np.ndarray:
        """Convert the screenshot to a NumPy array.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"HWC"``
            (default) or ``"CHW"``.
        :returns: A NumPy array of dtype ``uint8``.

        Use ``channels="BGR"`` for OpenCV, and ``channels="RGB"`` (the
        default) for scikit-image and most other frameworks.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        TODO(jholveck): After #536 is resolved, add a note about the
        buffer sharing semantics.
        """
        channels = cast("Channels", channels.upper())
        layout = cast("Layout", layout.upper())

        if channels not in {"BGRA", "BGR", "RGB", "RGBA"}:
            msg = "Channels must be 'BGRA', 'BGR', 'RGB', or 'RGBA'"
            raise ValueError(msg)
        if layout not in {"HWC", "CHW"}:
            msg = "Layout must be 'HWC' or 'CHW'"
            raise ValueError(msg)

        import numpy as np  # noqa: PLC0415

        frame = np.frombuffer(self._raw, dtype=np.uint8).reshape((self.height, self.width, 4))
        if channels == "BGRA":
            data = frame
        elif channels == "BGR":
            data = frame[:, :, :3]
        elif channels == "RGB":
            data = frame[:, :, [2, 1, 0]]
        else:  # RGBA
            data = frame[:, :, [2, 1, 0, 3]]

        if layout == "CHW":
            data = np.transpose(data, (2, 0, 1))

        return data

    def to_torch(
        self,
        channels: Channels = "RGB",
        layout: Layout = "CHW",
        dtype: torch.dtype | None = None,
    ) -> torch.Tensor:
        """Convert the screenshot to a PyTorch tensor.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"CHW"``
            (default) or ``"HWC"``.
        :param dtype: The requested dtype as a ``torch.dtype``.
            Defaults to ``torch.float32``.

        Floating point dtypes are scaled to the ``[0, 1]`` range.

        The default layout is ``"CHW"`` because it is more commonly used
        in PyTorch models.  This is different than in
        :py:meth:`to_numpy` or :py:meth:`to_tensorflow`, which default
        to ``"HWC"``.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        TODO(jholveck): After #536 is resolved, add a note about the
        buffer sharing semantics.
        """
        import torch  # noqa: PLC0415

        frame = self.to_numpy(channels=channels, layout=layout)

        if dtype is None:
            dtype = torch.float32
        elif not isinstance(dtype, torch.dtype):
            msg = 'argument "dtype" must be a torch.dtype'
            raise TypeError(msg)

        tensor = torch.from_numpy(frame)
        tensor = tensor.to(dtype=dtype)
        if dtype.is_floating_point:
            tensor = tensor / 255.0
        return tensor

    def to_tensorflow(
        self,
        channels: Channels = "RGB",
        layout: Layout = "HWC",
        dtype: tf.DType | np.dtype | int | str = "float32",
    ) -> tf.Tensor:
        """Convert the screenshot to a TensorFlow tensor.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"HWC"``
            (default) or ``"CHW"``.
        :param dtype: The requested dtype.  Can be a string like
            ``"float32"`` (default), a :py:class:``tf.DType``, an int
            representing a TensorFlow ``DataClass`` enum value, or a
            ``np.dtype``.

        Floating point dtypes are scaled to the ``[0, 1]`` range.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        Currently, the returned :py:class:`tf.Tensor` does not share
        memory with the :py:class:`ScreenShot`.  This is expected to
        change in the future.  TODO(jholveck): After #536 is resolved,
        add a note about the expected buffer sharing semantics.
        """
        import tensorflow as tf  # noqa: PLC0415

        frame = self.to_numpy(channels=channels, layout=layout)

        # TypeErrors from tf.as_dtype are passed up to the caller.
        tf_dtype = tf.as_dtype(dtype)

        tensor = tf.convert_to_tensor(frame, dtype=tf_dtype)
        if tf_dtype.is_floating:
            # TensorFlow's implicit dtype conversion rules are not trivial.  We use an explicit dtype on both sides
            # instead, by making a tf.constant.
            tensor = tensor / tf.constant(255.0, dtype=tf_dtype)
        return tensor

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
