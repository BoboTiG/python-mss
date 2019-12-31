"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""


class SimpleScreenShot:
    def __init__(self, data, monitor, **kwargs):
        self.raw = bytes(data)
        self.monitor = monitor


def test_custom_cls_image(sct):
    sct.cls_image = SimpleScreenShot
    mon1 = sct.monitors[1]
    image = sct.grab(mon1)
    assert isinstance(image, SimpleScreenShot)
    assert isinstance(image.raw, bytes)
    assert isinstance(image.monitor, dict)
