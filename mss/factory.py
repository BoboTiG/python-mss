# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import platform

from .exception import ScreenShotError


def mss(**kwargs):
    """ Factory returning a proper MSS class instance.

        It detects the plateform we are running on
        and choose the most adapted mss_class to take
        screenshots.

        It then proxies its arguments to the class for
        instantiation.
    """

    # pylint: disable=import-error

    operating_system = platform.system().lower()
    if operating_system == "darwin":
        from .darwin import MSS  # type: ignore
    elif operating_system == "linux":
        from .linux import MSS  # type: ignore
    elif operating_system == "windows":
        from .windows import MSS  # type: ignore
    else:
        raise ScreenShotError(
            "System {!r} not (yet?) implemented.".format(operating_system)
        )

    return MSS(**kwargs)
