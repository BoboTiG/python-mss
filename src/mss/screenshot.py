# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Literal, cast

from mss.exception import ScreenShotError
from mss.models import Monitor, Pixel, Pixels, Pos, Size

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

    # We don't import numpy as np, since their InterSphinx reference isn't set up with that shortcut.
    import numpy  # noqa: ICN001
    import PIL.Image
    import tensorflow as tf
    import torch
    from typing_extensions import Buffer

# Type checkers can see these, but they don't get into the Sphinx docs.  I'm not sure if we should do this differently.
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
        self.__pixels: Pixels | None = None
        self.__rgb: memoryview | None = None

        #: NamedTuple of the screenshot coordinates.
        self.pos: Pos = Pos(monitor["left"], monitor["top"])

        #: NamedTuple of the screenshot size.
        self.size: Size = Size(monitor["width"], monitor["height"]) if size is None else size

        # Buffer of the raw BGRA pixels, retrieved by the platform-specific implementations.
        self._raw: memoryview[int] = memoryview(data)
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
        :py:class:`ScreenShot` instance directly to these libraries without
        needing to convert it first.

        This is in HWC order, with 4 channels in BGRA order.

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
    def bgra(self) -> memoryview[int]:
        """BGRx values from the BGRx raw pixels.

        The format is a memoryview object of bytes.  These are in a
        BGRxBGRx... sequence.  A specific pixel can be accessed as
        ``bgra[(y * width + x) * 4:(y * width + x) * 4 + 4].``

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
    def raw(self) -> memoryview[int]:
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

    def to_pil(self, mode: str = "RGB") -> PIL.Image.Image:
        """Convert the screenshot to a Pillow image.

        :param mode: The requested image mode.  Must be ``"RGB"``
            (default) or ``"RGBA"``.

        When requesting ``"RGBA"``, the alpha channel may not represent
        meaningful transparency on all platforms/backends.

        .. version-added:: 11.0.0
        """
        mode = mode.upper()
        if mode not in {"RGB", "RGBA"}:
            msg = "Mode must be 'RGB' or 'RGBA'"
            raise ValueError(msg)

        from PIL import Image  # noqa: PLC0415

        raw_mode = "BGRX" if mode == "RGB" else "BGRA"
        return Image.frombuffer(mode, self.size, self._raw, "raw", raw_mode, 0, 1)

    def to_numpy(
        self, channels: Channels = "RGB", layout: Layout = "HWC", dtype: numpy.dtype | type | None = None
    ) -> numpy.ndarray:
        """Convert the screenshot to a NumPy array.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"HWC"``
            (default) or ``"CHW"``.
        :param dtype: The requested data type.  The default is
            ``np.uint8``.

        Floating point dtypes are scaled to the ``[0, 1]`` range.

        Use ``channels="BGR"`` for OpenCV, and ``channels="RGB"`` (the
        default) for scikit-image and most other frameworks.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        .. version-added:: 11.0.0
        """
        channels = cast("Channels", channels.upper())
        layout = cast("Layout", layout.upper())

        import numpy as np  # noqa: PLC0415

        rv = np.frombuffer(self._raw, dtype=np.uint8).reshape((self.height, self.width, 4))

        if channels == "BGRA":
            pass
        elif channels == "BGR":
            rv = rv[:, :, :3]
        elif channels == "RGB":
            # Using [2,1,0] instead of 2::-1 would copy, rather than creating a view.
            rv = rv[:, :, 2::-1]
        elif channels == "RGBA":
            # This can't be represented as a view, since the channels within a pixel are not ordered in a way that can
            # be represented with a constant offset.  In other words, the way that NumPy strides work, you can only make
            # a view if you can express the desired element order in a x:y:z style range relative to the base array's
            # order.
            rv = rv[:, :, [2, 1, 0, 3]]
        else:
            msg = 'Channels must be "BGRA", "BGR", "RGB", or "RGBA"'
            raise ValueError(msg)

        if layout == "HWC":
            pass
        elif layout == "CHW":
            # This will always create a view.  (We're reordering the axes, not the elements.)
            rv = np.transpose(rv, (2, 0, 1))
        else:
            msg = 'Layout must be "HWC" or "CHW"'
            raise ValueError(msg)

        dtype = np.uint8 if dtype is None else np.dtype(dtype)
        if dtype != np.uint8:
            rv = rv.astype(dtype)
            if np.issubdtype(dtype, np.floating):
                rv /= 255.0

        return rv

    def to_torch(  # noqa: PLR0912
        self,
        channels: Channels = "RGB",
        layout: Layout = "CHW",
        dtype: torch.dtype | None = None,
        device: torch.device | str | None = None,
    ) -> torch.Tensor:
        """Convert the screenshot to a PyTorch tensor.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"CHW"``
            (default) or ``"HWC"``.
        :param dtype: The requested dtype as a :py:class:`torch.dtype`.
            Defaults to the current PyTorch default dtype, which is
            usually ``torch.float32``; see
            :py:func:`torch.get_default_dtype`.
        :param device: The requested destination device, as a
            :py:class:`torch.device` or string.  Default is the current
            default PyTorch device; see
            :py:func:`torch.get_default_device`.

        Floating point dtypes are scaled to the ``[0, 1]`` range.

        The default layout is ``"CHW"`` because it is more commonly used
        in PyTorch models.  This is different than in
        :py:meth:`to_numpy` or :py:meth:`to_tensorflow`, which default
        to ``"HWC"``.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        .. version-added:: 11.0.0
        """
        channels = cast("Channels", channels.upper())
        layout = cast("Layout", layout.upper())

        import torch  # noqa: PLC0415

        if dtype is None:
            torch_dtype = torch.get_default_dtype()
        elif isinstance(dtype, torch.dtype):
            torch_dtype = dtype
        else:
            msg = 'argument "dtype" must be a torch.dtype'
            raise TypeError(msg)
        torch_device = torch.get_default_device() if device is None else torch.device(device)

        if torch_device.type == "cpu":
            # NumPy handles the necessary CPU operations significantly more efficiently than PyTorch, so we defer to it.
            ndarray = self.to_numpy(channels=channels, layout=layout)
            # to_numpy can return tensors with negative strides, which PyTorch doesn't support.
            if any(s < 0 for s in ndarray.strides):
                ndarray = ndarray.copy()
            rv = torch.from_numpy(ndarray)
            # We do the dtype conversion ourselves because PyTorch has dtypes that NumPy doesn't, like bfloat16.
            rv = rv.to(dtype=torch_dtype, device=torch_device)
            if torch_dtype.is_floating_point:
                rv.div_(255.0)
            return rv

        # Build a new tensor from the raw bytes.  This is a view, not a copy.  The shape is HWC with 4 channels in BGRA
        # order at this point.  The dtype here tells PyTorch how to interpret the data (unlike TensorFlow's
        # convert_to_tensor with a memoryview).
        rv = torch.frombuffer(self._raw, dtype=torch.uint8)
        rv = rv.reshape((self.height, self.width, 4))

        # Move the data to the desired device.  If no copy is needed, this is a no-op.  PyTorch using CUDA can do this
        # transfer without blocking; the other devices can't.  (Well, they technically can, but then our subsequent ops
        # may corrupt data unless we synchronize explicitly.)
        rv = rv.to(device=torch_device, non_blocking=(torch_device.type == "cuda"))

        if channels == "BGRA":
            pass
        elif channels == "BGR":
            rv = rv[:, :, :3]
        elif channels == "RGB":
            # We can't use 2::-1 with PyTorch, since it doesn't support negative strides.  We always have to copy.
            rv = rv[:, :, [2, 1, 0]]
        elif channels == "RGBA":
            # This can't be represented as a view; see the comment in the NumPy version.
            rv = rv[:, :, [2, 1, 0, 3]]
        else:
            msg = 'Channels must be "BGRA", "BGR", "RGB", or "RGBA"'
            raise ValueError(msg)

        if layout == "HWC":
            pass
        elif layout == "CHW":
            rv = rv.movedim((2, 0, 1), (0, 1, 2))
        else:
            msg = 'Layout must be "HWC" or "CHW"'
            raise ValueError(msg)

        # Do the conversion last to save memory bandwidth during channel shuffles.
        rv = rv.to(dtype=torch_dtype)
        if torch_dtype.is_floating_point:
            rv.div_(255.0)

        return rv

    def to_tensorflow(
        self,
        channels: Channels = "RGB",
        layout: Layout = "HWC",
        dtype: tf.dtypes.DType | numpy.dtype | str = "float32",
    ) -> tf.Tensor:
        """Convert the screenshot to a TensorFlow tensor.

        :param channels: The requested channel order.  Must be
            ``"BGRA"``, ``"BGR"``, ``"RGB"`` (default), or ``"RGBA"``.
        :param layout: The requested layout.  Must be ``"HWC"``
            (default) or ``"CHW"``.
        :param dtype: The requested dtype.  Can be a string like
            ``"float32"`` (default), a :py:class:`tf.DType
            <tf.dtypes.DType>`, or a :py:class:`np.dtype <numpy.dtype>`.

        Device and stream management is handled by TensorFlow.

        Floating point dtypes are scaled to the ``[0, 1]`` range.

        When requesting ``"RGBA"`` or ``"BGRA"``, the alpha channel may
        not represent meaningful transparency on all platforms/backends.

        .. version-added:: 11.0.0
        """
        channels = cast("Channels", channels.upper())
        layout = cast("Layout", layout.upper())

        import tensorflow as tf  # noqa: PLC0415

        # TypeErrors from tf.as_dtype are passed up to the caller.
        tf_dtype = tf.as_dtype(dtype)

        # We don't need to do anything explicit about device management in TensorFlow; it handles that for us.
        # convert_to_tensor will always copy.  We verified in __init__ that self._raw is a memoryview of unsigned bytes,
        # so that's what TensorFlow will take as the source format; we just give an explicit dtype for clarity.
        rv = tf.convert_to_tensor(self._raw, dtype=tf.uint8)
        rv = tf.reshape(rv, (self.height, self.width, 4))

        if channels == "BGRA":
            pass
        elif channels == "BGR":
            rv = rv[:, :, :3]
        elif channels == "RGB":
            rv = tf.gather(rv, [2, 1, 0], axis=2)
        elif channels == "RGBA":
            rv = tf.gather(rv, [2, 1, 0, 3], axis=2)
        else:
            msg = 'Channels must be "BGRA", "BGR", "RGB", or "RGBA"'
            raise ValueError(msg)

        if layout == "HWC":
            pass
        elif layout == "CHW":
            rv = tf.transpose(rv, perm=(2, 0, 1))
        else:
            msg = 'Layout must be "HWC" or "CHW"'
            raise ValueError(msg)

        # Do the conversion last to save memory bandwidth during channel shuffles.
        if tf_dtype != tf.uint8:
            rv = tf.cast(rv, dtype=tf_dtype)
            if tf_dtype.is_floating:
                # TensorFlow's implicit dtype conversion rules are not trivial.  We use an explicit dtype on both sides
                # instead, by making a tf.constant.
                rv = rv / tf.constant(255.0, dtype=tf_dtype)

        return rv

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
