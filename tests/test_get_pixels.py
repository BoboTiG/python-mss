# coding: utf-8


def test_get_pixels(sct):
    mon1 = sct.enum_display_monitors()[1]
    pixels = sct.get_pixels(mon1)
    assert pixels is sct.image
    assert isinstance(sct.image, bytes)


def test_get_pixels_part_of_screen_no_strides(sct):
    mon = {'top': 160, 'left': 160, 'width': 160, 'height': 160}
    pixels = sct.get_pixels(mon)
    assert pixels is sct.image
    assert isinstance(sct.image, bytes)
    assert sct.width == 160
    assert sct.height == 160


def test_get_pixels_part_of_screen_strides(sct):
    mon = {'top': 160, 'left': 160, 'width': 222, 'height': 42}
    pixels = sct.get_pixels(mon)
    assert pixels is sct.image
    assert isinstance(sct.image, bytes)
    assert sct.width == 222
    assert sct.height == 42
