from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError


def mss(backend: str = "default", **kwargs: Any) -> MSSBase:
    backend = backend.lower()
    if backend in {"default", "xlib"}:
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend == "xgetimage":
        from . import xgetimage  # noqa: PLC0415

        return xgetimage.MSS(**kwargs)
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)


# Alias in upper-case for backward compatibility.  This is a supported name in the docs.
def MSS(*args, **kwargs) -> MSSBase:  # type: ignore[no-untyped-def] # noqa: N802, ANN002, ANN003
    return mss(*args, **kwargs)
