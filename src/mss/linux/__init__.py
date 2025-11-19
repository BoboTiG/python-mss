from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError


# This factory function is named in upper-case for backwards compatibility.
def MSS(backend: str = "default", **kwargs: Any) -> MSSBase:  # noqa: N802
    backend = backend.lower()
    if backend in {"default", "xlib"}:
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend == "xgetimage":
        from . import xgetimage  # noqa: PLC0415

        return xgetimage.MSS(**kwargs)
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)
