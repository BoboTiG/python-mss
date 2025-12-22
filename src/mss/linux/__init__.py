"""GNU/Linux backend dispatcher for X11 screenshot implementations."""

from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError

BACKENDS = ["default", "xlib", "xgetimage", "xshmgetimage"]


def mss(backend: str = "default", **kwargs: Any) -> MSSBase:
    """Return a backend-specific MSS implementation for GNU/Linux.

    Selects and instantiates the appropriate X11 backend based on the
    ``backend`` parameter.

    :param backend: Backend selector. Valid values:

        - ``"default"`` or ``"xshmgetimage"`` (default): XCB-based backend
          using XShmGetImage with automatic fallback to XGetImage when MIT-SHM
          is unavailable; see :py:class:`mss.linux.xshmgetimage.MSS`.
        - ``"xgetimage"``: XCB-based backend using XGetImage;
          see :py:class:`mss.linux.xgetimage.MSS`.
        - ``"xlib"``: Legacy Xlib-based backend retained for environments
          without working XCB libraries; see :py:class:`mss.linux.xlib.MSS`.

        .. versionadded:: 10.2.0 Prior to this version, the
            :class:`mss.linux.xlib.MSS` implementation was the only available
            backend.

    :param display: Optional keyword argument.  Specifies an X11 display
        string to connect to.  The default is taken from the environment
        variable :envvar:`DISPLAY`.
    :type display: str | bytes | None
    :param kwargs: Additional keyword arguments passed to the backend class.
    :returns: An MSS backend implementation.

    .. versionadded:: 10.2.0 Prior to this version, this didn't exist:
         the :func:`mss.linux.MSS` was a class equivalent to the current
         :class:`mss.linux.xlib.MSS` implementation.
    """
    backend = backend.lower()
    if backend == "xlib":
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend == "xgetimage":
        from . import xgetimage  # noqa: PLC0415

        # Note that the xshmgetimage backend will automatically fall back to XGetImage calls if XShmGetImage isn't
        # available.  The only reason to use the xgetimage backend is if the user already knows that XShmGetImage
        # isn't going to be supported.
        return xgetimage.MSS(**kwargs)
    if backend in {"default", "xshmgetimage"}:
        from . import xshmgetimage  # noqa: PLC0415

        return xshmgetimage.MSS(**kwargs)
    assert backend not in BACKENDS  # noqa: S101
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)


# Alias in upper-case for backward compatibility.  This is a supported name in the docs.
def MSS(*args, **kwargs) -> MSSBase:  # type: ignore[no-untyped-def] # noqa: N802, ANN002, ANN003
    """Alias for :func:`mss.linux.mss.mss` for backward compatibility.

    .. versionchanged:: 10.2.0 Prior to this version, this was a class.
    .. deprecated:: 10.2.0 Use :func:`mss.linux.mss` instead.
    """
    return mss(*args, **kwargs)
