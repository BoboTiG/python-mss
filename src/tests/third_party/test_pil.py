"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable
import itertools
import os
import os.path
from pathlib import Path

import pytest

from mss import mss
from mss.base import MSSBase

Image = pytest.importorskip("PIL.Image", reason="PIL module not available.")


def test_pil(mss_impl: Callable[..., MSSBase]) -> None:
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss_impl() as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    output = Path("box.png")
    img.save(output)
    assert output.is_file()


def test_pil_bgra(mss_impl: Callable[..., MSSBase]) -> None:
    width, height = 16, 16
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss_impl() as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    output = Path("box-bgra.png")
    img.save(output)
    assert output.is_file()


def test_pil_not_16_rounded(mss_impl: Callable[..., MSSBase]) -> None:
    width, height = 10, 10
    box = {"top": 0, "left": 0, "width": width, "height": height}
    with mss_impl() as sct:
        sct_img = sct.grab(box)

    img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
    assert img.mode == "RGB"
    assert img.size == sct_img.size

    for x, y in itertools.product(range(width), range(height)):
        assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    output = Path("box.png")
    img.save(output)
    assert output.is_file()
