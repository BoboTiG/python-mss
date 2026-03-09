# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from mss.exception import ScreenShotError
from mss.models import Monitor, Pixel, Pixels, Pos, Size

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Iterator

    import numpy as np
    import PIL.Image
    import tensorflow as tf
    import torch

Channels = Literal["BGRA", "BGR", "RGB", "RGBA"]
Layout = Literal["HWC", "CHW"]


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
        pixel can be accessed as
        ``bgra[(y * width + x) * 4:(y * width + x) * 4 + 4].``

        .. note::
            While the name is ``bgra``, the alpha channel may or may not be
            valid.
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
        pixel can be accessed as
        ``rgb[(y * width + x) * 3:(y * width + x) * 3 + 3]``.
        """
        if not self.__rgb:
            rgb = bytearray(self.height * self.width * 3)
            raw = self.raw
            rgb[::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[::4]
            self.__rgb = bytes(rgb)

        return self.__rgb

    def to_pil(self, mode: str = "RGB") -> PIL.Image.Image:
        """Convert the screenshot to a Pillow image.

        Args:
            mode: The requested image mode.  Must be ``"RGB"``
                (default) or ``"RGBA"``.

        Returns:
            A :class:`PIL.Image.Image` instance.

        Notes:
            When requesting ``"RGBA"``, the alpha channel may not be
            meaningful on all platforms/backends.

            Use ``channels="BGR"`` for OpenCV, and ``channels="RGB"``
            (the default) for scikit-image and most other frameworks.
        """
        mode = mode.upper()
        if mode not in {"RGB", "RGBA"}:
            msg = "Mode must be 'RGB' or 'RGBA'"
            raise ValueError(msg)

        from PIL import Image  # noqa: PLC0415

        raw_mode = "BGRX" if mode == "RGB" else "BGRA"
        return Image.frombuffer(mode, self.size, self.raw, "raw", raw_mode, 0, 1)

    def to_numpy(self, channels: Channels = "RGB", layout: Layout = "HWC") -> np.ndarray:
        """Convert the screenshot to a NumPy array.

        Args:
            channels: The requested channel order.  Must be
                ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or
                ``"RGBA"``.
            layout: The requested layout.  Must be ``"HWC"`` (default)
                or ``"CHW"``.

        Returns:
            A NumPy array of dtype ``uint8``.

        Notes:
            When requesting ``"RGBA"``, the alpha channel may not be
            meaningful on all platforms/backends.
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

        frame = np.frombuffer(self.raw, dtype=np.uint8).reshape((self.height, self.width, 4))
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

        Args:
            channels: The requested channel order.  Must be
                ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or
                ``"RGBA"``.
            layout: The requested layout.  Must be ``"CHW"`` (default)
                or ``"HWC"``.
            dtype: The requested dtype as a ``torch.dtype``.  Defaults to
                ``torch.float32``.

        Returns:
            A PyTorch tensor.

        Notes:
            The default layout is ``"CHW"`` because it is more
            commonly used in PyTorch models.  This is different than
            in :py:meth:`to_numpy` or :py:meth:`to_tensorflow`, which
            default to ``"HWC"``.

            When requesting ``"RGBA"``, the alpha channel may not be
            meaningful on all platforms/backends.

            Floating point dtypes are scaled to the ``[0, 1]`` range.
        """
        import torch  # noqa: PLC0415

        frame = self.to_numpy(channels=channels, layout=layout)

        if dtype is None:
            dtype = torch.float32
        elif not isinstance(dtype, torch.dtype):
            msg = "Dtype must be a torch dtype"
            raise ValueError(msg)

        tensor = torch.from_numpy(frame)
        tensor = tensor.to(dtype=dtype)
        if dtype.is_floating_point:
            tensor = tensor / 255.0
        return tensor

    def to_tensorflow(
        self,
        channels: Channels = "RGB",
        layout: Layout = "HWC",
        dtype: tf.DType | str = "float32",
    ) -> tf.Tensor:
        """Convert the screenshot to a TensorFlow tensor.

        Args:
            channels: The requested channel order.  Must be
                ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or
                ``"RGBA"``.
            layout: The requested layout.  Must be ``"HWC"`` (default)
                or ``"CHW"``.
            dtype: The requested dtype.  Can be a string like
                ``"float32"`` (default) or a ``tf.DType``.

        Returns:
            A TensorFlow tensor.

        Notes:
            When requesting ``"RGBA"``, the alpha channel may not be
            meaningful on all platforms/backends.

            Floating point dtypes are scaled to the ``[0, 1]`` range.
        """
        import tensorflow as tf  # noqa: PLC0415

        frame = self.to_numpy(channels=channels, layout=layout)

        try:
            tf_dtype = tf.as_dtype(dtype)
        except (TypeError, ValueError) as exc:
            msg = "Dtype must be a TensorFlow DType or valid string"
            raise ValueError(msg) from exc

        tensor = tf.convert_to_tensor(frame, dtype=tf_dtype)
        if tf_dtype.is_floating:
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
