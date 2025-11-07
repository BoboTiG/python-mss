from typing import Any

from ..base import MSSBase
from ..exception import ScreenShotError


def MSS(backend: str = "xlib", **kwargs: Any) -> MSSBase:
    backend = backend.lower()
    if backend == "xlib":
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend in {"xcb", "getimage"}:
        from . import getimage  # noqa: PLC0415

        return getimage.MSS(**kwargs)
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)
