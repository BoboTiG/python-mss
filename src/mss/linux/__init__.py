"""GNU/Linux backend dispatcher.

This module picks the appropriate X11 backend implementation based on the
``backend`` option. Available values:

- ``"default"`` or ``"xshmgetimage"``: XCB-based backend using XShmGetImage
    with automatic fallback to XGetImage when MIT-SHM is unavailable (default)
- ``"xgetimage"``: XCB-based backend using XGetImage
- ``"xlib"``: legacy Xlib-based backend retained for environments without
    working XCB libraries

Keyword arguments are forwarded to the selected backend. The ``display``
argument (e.g., ``":0.0"``) targets a specific X server when needed.

.. versionadded:: 10.2.0
   The ``backend`` selector and the upper-case :func:`MSS` alias.

The top-level :func:`mss` function proxies keyword arguments to the selected
backend class and returns an :class:`mss.base.MSSBase` implementation.
"""

from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError

BACKENDS = ["default", "xlib", "xgetimage", "xshmgetimage"]


def mss(backend: str = "default", **kwargs: Any) -> MSSBase:
    """Return a backend-specific MSS implementation.

    The ``backend`` flag selects the implementation:

    - ``"default"``/``"xshmgetimage"`` (default): XCB backend using
      XShmGetImage with automatic fallback to XGetImage
    - ``"xgetimage"``: XCB backend using XGetImage
    - ``"xlib"``: traditional Xlib backend retained for environments without
      working XCB libraries
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
    return mss(*args, **kwargs)
