from typing import Any

from ..base import MSSBase
from ..exception import ScreenShotError


def MSS(backend: str = "xlib", **kwargs: Any) -> MSSBase:
    backend = backend.lower()
    if backend in {"default", "xlib"}:
        from . import xlib  # noqa: PLC0415

        return xlib.MSS(**kwargs)
    if backend == "xgetimage":
        from . import xgetimage  # noqa: PLC0415

        return xgetimage.MSS(**kwargs)
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)
