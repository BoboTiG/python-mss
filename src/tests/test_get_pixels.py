"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import itertools
import os

import pytest

from mss import mss
from mss.base import ScreenShot
from mss.exception import ScreenShotError


def test_grab_monitor():
    with mss(display=os.getenv("DISPLAY")) as sct:
        for mon in sct.monitors:
            image = sct.grab(mon)
            assert isinstance(image, ScreenShot)
            assert isinstance(image.raw, bytearray)
            assert isinstance(image.rgb, bytes)


def test_grab_part_of_screen(pixel_ratio):
    with mss(display=os.getenv("DISPLAY")) as sct:
        for width, height in itertools.product(range(1, 42), range(1, 42)):
            monitor = {"top": 160, "left": 160, "width": width, "height": height}
            image = sct.grab(monitor)

            assert image.top == 160
            assert image.left == 160
            assert image.width == width * pixel_ratio
            assert image.height == height * pixel_ratio


def test_get_pixel(raw: bytes):
    image = ScreenShot.from_size(bytearray(raw), 1024, 768)
    assert image.width == 1024
    assert image.height == 768
    assert len(image.pixels) == 768
    assert len(image.pixels[0]) == 1024

    assert image.pixel(0, 0) == (135, 152, 192)
    assert image.pixel(image.width // 2, image.height // 2) == (0, 0, 0)
    assert image.pixel(image.width - 1, image.height - 1) == (135, 152, 192)

    with pytest.raises(ScreenShotError):
        image.pixel(image.width + 1, 12)
