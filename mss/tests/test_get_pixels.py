"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import pytest
from mss.base import ScreenShot
from mss.exception import ScreenShotError


def test_grab_monitor(sct):
    for mon in sct.monitors:
        image = sct.grab(mon)
        assert isinstance(image, ScreenShot)
        assert isinstance(image.raw, bytearray)
        assert isinstance(image.rgb, bytes)


def test_grab_part_of_screen(sct, pixel_ratio):
    monitor = {"top": 160, "left": 160, "width": 160, "height": 160}
    image = sct.grab(monitor)
    assert isinstance(image, ScreenShot)
    assert isinstance(image.raw, bytearray)
    assert isinstance(image.rgb, bytes)
    assert image.top == 160
    assert image.left == 160
    assert image.width == 160 * pixel_ratio
    assert image.height == 160 * pixel_ratio


def test_grab_part_of_screen_rounded(sct, pixel_ratio):
    monitor = {"top": 160, "left": 160, "width": 161, "height": 159}
    image = sct.grab(monitor)
    assert isinstance(image, ScreenShot)
    assert isinstance(image.raw, bytearray)
    assert isinstance(image.rgb, bytes)
    assert image.top == 160
    assert image.left == 160
    assert image.width == 161 * pixel_ratio
    assert image.height == 159 * pixel_ratio


def test_grab_individual_pixels(sct):
    monitor = {"top": 160, "left": 160, "width": 222, "height": 42}
    image = sct.grab(monitor)
    assert isinstance(image.pixel(0, 0), tuple)
    with pytest.raises(ScreenShotError):
        image.pixel(image.width + 1, 12)
