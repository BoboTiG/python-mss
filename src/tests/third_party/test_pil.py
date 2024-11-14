"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import itertools
import os
import os.path

import pytest

from mss import mss

Image = pytest.importorskip("PIL.Image", reason="PIL module not available.")


def test_pil() -> None:
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss(display=os.getenv("DISPLAY")) as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box.png")
    assert os.path.isfile("box.png")


def test_pil_bgra() -> None:
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss(display=os.getenv("DISPLAY")) as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box-bgra.png")
    assert os.path.isfile("box-bgra.png")


def test_pil_not_16_rounded() -> None:
    width, height = 10, 10
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss(display=os.getenv("DISPLAY")) as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save("box.png")
    assert os.path.isfile("box.png")
