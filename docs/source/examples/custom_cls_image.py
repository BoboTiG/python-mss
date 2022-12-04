"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Screenshot of the monitor 1, using a custom class to handle the data.
"""
from typing import Any

import mss
from mss.models import Monitor
from mss.screenshot import ScreenShot


class SimpleScreenShot(ScreenShot):
    """
    Define your own custom method to deal with screen shot raw data.
    Of course, you can inherit from the ScreenShot class and change
    or add new methods.
    """

    def __init__(self, data: bytearray, monitor: Monitor, **_: Any) -> None:
        self.data = data
        self.monitor = monitor


with mss.mss() as sct:
    sct.cls_image = SimpleScreenShot
    image = sct.grab(sct.monitors[1])
    # ...
