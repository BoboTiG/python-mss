"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform
from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError


def mss(**kwargs: Any) -> MSSBase:
    """Factory returning a proper MSS class instance.

    It detects the platform we are running on
    and chooses the most adapted mss_class to take
    screenshots.

    It then proxies its arguments to the class for
    instantiation.
    """
    os_ = platform.system().lower()

    if os_ == "darwin":
        from mss import darwin

        return darwin.MSS(**kwargs)

    if os_ == "linux":
        from mss import linux

        return linux.MSS(**kwargs)

    if os_ == "windows":
        from mss import windows

        return windows.MSS(**kwargs)

    msg = f"System {os_!r} not (yet?) implemented."
    raise ScreenShotError(msg)
