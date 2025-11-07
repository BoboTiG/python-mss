"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable
import itertools
import os

import pytest

from mss import mss
from mss.base import MSSBase, ScreenShot
from mss.exception import ScreenShotError


def test_grab_monitor(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        for mon in sct.monitors:
            image = sct.grab(mon)
            assert isinstance(image, ScreenShot)
            assert isinstance(image.raw, bytearray)
            assert isinstance(image.rgb, bytes)


def test_grab_part_of_screen(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        for width, height in itertools.product(range(1, 42), range(1, 42)):
            monitor = {"top": 160, "left": 160, "width": width, "height": height}
            image = sct.grab(monitor)

            assert image.top == 160
            assert image.left == 160
            assert image.width == width
            assert image.height == height


def test_get_pixel(raw: bytes) -> None:
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
