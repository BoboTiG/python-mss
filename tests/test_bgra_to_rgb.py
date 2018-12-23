# coding: utf-8

from mss.base import ScreenShot

import pytest


def test_bad_length():
    data = bytearray(b"789c626001000000ffff030000060005")
    image = ScreenShot.from_size(data, 1024, 768)
    with pytest.raises(ValueError):
        image.rgb


def test_good_types(raw):
    image = ScreenShot.from_size(bytearray(raw), 1024, 768)
    assert isinstance(image.raw, bytearray)
    assert isinstance(image.rgb, bytes)
