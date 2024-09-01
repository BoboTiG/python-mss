"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os
from typing import Any

from mss import mss
from mss.models import Monitor


class SimpleScreenShot:
    def __init__(self, data: bytearray, monitor: Monitor, **_: Any) -> None:
        self.raw = bytes(data)
        self.monitor = monitor


def test_custom_cls_image() -> None:
    with mss(display=os.getenv("DISPLAY")) as sct:
        sct.cls_image = SimpleScreenShot  # type: ignore[assignment]
        mon1 = sct.monitors[1]
        image = sct.grab(mon1)
    assert isinstance(image, SimpleScreenShot)
    assert isinstance(image.raw, bytes)
    assert isinstance(image.monitor, dict)
