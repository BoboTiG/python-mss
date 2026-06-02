"""GNU/Linux backend dispatcher for X11 screenshot implementations."""

import warnings
from typing import Any

from mss.base import MSS as _MSS
from mss.base import MSSImplementation
from mss.exception import ScreenShotError

# TODO(jholveck): #493 Remove these legacy symbol re-exports after 10.x transition period.
from mss.linux.xlib import (  # noqa: F401
    CFUNCTIONS,
    PLAINMASK,
    ZPIXMAP,
    Display,
    XErrorEvent,
    XFixesCursorImage,
    XImage,
    XRRCrtcInfo,
    XRRModeInfo,
    XRRScreenResources,
    XWindowAttributes,
)

__all__ = ["MSS"]

BACKENDS = ["default", "xlib", "xgetimage", "xshmgetimage"]


class MSS(_MSS):
    """Deprecated GNU/Linux compatibility constructor.

    Use :class:`mss.MSS` instead.
    """

    def __init__(self, /, **kwargs: Any) -> None:
        # TODO(jholveck): #493 Remove compatibility constructor after 10.x transition period.
        warnings.warn(
            "mss.linux.MSS is deprecated and will be removed in 11.0; use mss.MSS instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)


def choose_impl(backend: str = "default", **kwargs: Any) -> MSSImplementation:
    """Return a backend-specific MSS implementation for GNU/Linux.

    Selects and instantiates the appropriate X11 backend based on the
    ``backend`` parameter.

    :param backend: Backend selector. Valid values:

        - ``"default"`` or ``"xshmgetimage"`` (default): XCB-based backend
          using XShmGetImage with automatic fallback to XGetImage when MIT-SHM
          is unavailable.
        - ``"xgetimage"``: XCB-based backend using XGetImage.
        - ``"xlib"``: Legacy Xlib-based backend retained for environments
          without working XCB libraries.

        .. versionadded:: 10.2.0 Prior to this version, the
            legacy Xlib implementation was the only available
            backend.

    :param display: Optional keyword argument.  Specifies an X11 display
        string to connect to.  The default is taken from the environment
        variable :envvar:`DISPLAY`.
    :type display: str | bytes | None
    :param kwargs: Additional keyword arguments passed to the backend class.
    :returns: An MSS backend implementation.

    .. versionadded:: 10.2.0 Prior to this version, this didn't exist:
          GNU/Linux had a single implementation selected through
          :class:`mss.linux.MSS`.
    """
    backend = backend.lower()
    if backend == "xlib":
        from mss.linux.xlib import MSSImplXlib  # noqa: PLC0415

        return MSSImplXlib(**kwargs)
    if backend == "xgetimage":
        from mss.linux.xgetimage import MSSImplXGetImage  # noqa: PLC0415

        # Note that the xshmgetimage backend will automatically fall back to XGetImage calls if XShmGetImage isn't
        # available.  The only reason to use the xgetimage backend is if the user already knows that XShmGetImage
        # isn't going to be supported.
        return MSSImplXGetImage(**kwargs)
    if backend in {"default", "xshmgetimage"}:
        from mss.linux.xshmgetimage import MSSImplXShmGetImage  # noqa: PLC0415

        return MSSImplXShmGetImage(**kwargs)
    assert backend not in BACKENDS  # noqa: S101
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)
