from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError


def mss(backend: str = "default", **kwargs: Any) -> MSSBase:
    """Factory returning a proper MSS class instance.

    It examines the options provided, and chooses the most adapted MSS
    class to take screenshots.  It then proxies its arguments to the
    class for instantiation.

    Currently, the only option used is the "backend" flag.  Future
    versions will look at other options as well.
    """
    backend = backend.lower()
    if backend in {"default", "xlib"}:
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend == "xgetimage":
        from . import xgetimage  # noqa: PLC0415

        # Note that the xshmgetimage backend will automatically fall
        # back to XGetImage calls if XShmGetImage isn't available.  The
        # only reason to use the xgetimage backend is if the user
        # already knows that XShmGetImage isn't going to be supported.
        return xgetimage.MSS(**kwargs)
    if backend == "xshmgetimage":
        from . import xshmgetimage  # noqa: PLC0415

        return xshmgetimage.MSS(**kwargs)
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)


# Alias in upper-case for backward compatibility.  This is a supported name in the docs.
def MSS(*args, **kwargs) -> MSSBase:  # type: ignore[no-untyped-def] # noqa: N802, ANN002, ANN003
    return mss(*args, **kwargs)
