"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import itertools
import os
import os.path

import pytest

try:
    import numpy
except (ImportError, RuntimeError):
    # RuntimeError on Python 3.9 (macOS): Polyfit sanity test emitted a warning, ...
    numpy = None

try:
    from PIL import Image
except ImportError:
    Image = None


@pytest.mark.skipif(numpy is None, reason="Numpy module not available.")
def test_numpy(sct, pixel_ratio):
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    img = numpy.array(sct.grab(box))
    assert len(img) == 10 * pixel_ratio


@pytest.mark.skipif(Image is None, reason="PIL module not available.")
def test_pil(sct):
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box.png")
    assert os.path.isfile("box.png")


@pytest.mark.skipif(Image is None, reason="PIL module not available.")
def test_pil_bgra(sct):
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box-bgra.png")
    assert os.path.isfile("box-bgra.png")


@pytest.mark.skipif(Image is None, reason="PIL module not available.")
def test_pil_not_16_rounded(sct):
    width, height = 10, 10
    box = {"top": 0, "left": 0, "width": width, "height": height}
    sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box.png")
    assert os.path.isfile("box.png")
