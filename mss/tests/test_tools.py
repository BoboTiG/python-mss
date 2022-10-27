"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import hashlib
import os.path
import zlib

import pytest

from mss.tools import to_png

WIDTH = 10
HEIGHT = 10
MD5SUM = "055e615b74167c9bdfea16a00539450c"


def test_bad_compression_level(sct):
    sct.compression_level = 42
    try:
        with pytest.raises(zlib.error):
            sct.shot()
    finally:
        sct.compression_level = 6


def test_compression_level(sct):
    data = b"rgb" * WIDTH * HEIGHT
    output = f"{WIDTH}x{HEIGHT}.png"

    to_png(data, (WIDTH, HEIGHT), level=sct.compression_level, output=output)
    with open(output, "rb") as png:
        assert hashlib.md5(png.read()).hexdigest() == MD5SUM


@pytest.mark.parametrize(
    "level, checksum",
    [
        (0, "f37123dbc08ed7406d933af11c42563e"),
        (1, "7d5dcf2a2224445daf19d6d91cf31cb5"),
        (2, "bde05376cf51cf951e26c31c5f55e9d5"),
        (3, "3d7e73c2a9c2d8842b363eeae8085919"),
        (4, "9565a5caf89a9221459ee4e02b36bf6e"),
        (5, "4d722e21e7d62fbf1e3154de7261fc67"),
        (6, "055e615b74167c9bdfea16a00539450c"),
        (7, "4d88d3f5923b6ef05b62031992294839"),
        (8, "4d88d3f5923b6ef05b62031992294839"),
        (9, "4d88d3f5923b6ef05b62031992294839"),
    ],
)
def test_compression_levels(level, checksum):
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT), level=level)
    md5 = hashlib.md5(raw).hexdigest()
    assert md5 == checksum


def test_output_file():
    data = b"rgb" * WIDTH * HEIGHT
    output = f"{WIDTH}x{HEIGHT}.png"
    to_png(data, (WIDTH, HEIGHT), output=output)

    assert os.path.isfile(output)
    with open(output, "rb") as png:
        assert hashlib.md5(png.read()).hexdigest() == MD5SUM


def test_output_raw_bytes():
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT))
    assert hashlib.md5(raw).hexdigest() == MD5SUM
