#!/usr/bin/env python
# coding: utf-8


def test_get_pixels(mss):
    mon1 = mss.enum_display_monitors()[1]
    pixels = mss.get_pixels(mon1)
    assert pixels is mss.image
    assert isinstance(mss.image, bytes)
