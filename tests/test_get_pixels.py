#!/usr/bin/env python
# coding: utf-8


def test_get_pixels(sct):
    mon1 = sct.enum_display_monitors()[1]
    pixels = sct.get_pixels(mon1)
    assert pixels is sct.image
    assert isinstance(sct.image, bytes)
