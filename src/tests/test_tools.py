"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import hashlib
import zlib
from collections.abc import Callable
from pathlib import Path

import pytest

from mss.base import MSSBase
from mss.tools import to_png

WIDTH = 10
HEIGHT = 10
MD5SUM = "ee1b645cc989cbfc48e613b395a929d3d79a922b77b9b38e46647ff6f74acef5"


def test_bad_compression_level(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl(compression_level=42) as sct, pytest.raises(zlib.error):
        sct.shot()


def test_compression_level(mss_impl: Callable[..., MSSBase]) -> None:
    data = b"rgb" * WIDTH * HEIGHT
    output = Path(f"{WIDTH}x{HEIGHT}.png")

    with mss_impl() as sct:
        to_png(data, (WIDTH, HEIGHT), level=sct.compression_level, output=output)

    assert hashlib.sha256(output.read_bytes()).hexdigest() == MD5SUM


@pytest.mark.parametrize(
    ("level", "checksum"),
    [
        (0, "547191069e78eef1c5899f12c256dd549b1338e67c5cd26a7cbd1fc5a71b83aa"),
        (1, "841665ec73b641dfcafff5130b497f5c692ca121caeb06b1d002ad3de5c77321"),
        (2, "b11107163207f68f36294deb3f8e6b6a5a11399a532917bdd59d1d5f1117d4d0"),
        (3, "31278bad8c1c077c715ac4f3b497694a323a71a87c5ff8bdc7600a36bd8d8c96"),
        (4, "8f7237e1394d9ddc71fcb1fa4a2c2953087562ef6eac85d32d8154b61b287fb0"),
        (5, "83a55f161bad2d511b222dcd32059c9adf32c3238b65f9aa576f19bc0a6c8fec"),
        (6, "ee1b645cc989cbfc48e613b395a929d3d79a922b77b9b38e46647ff6f74acef5"),
        (7, "85f8d1b01cef926c111b194229bd6c01e2a65b18b4dd902293698e6de8f4e9ac"),
        (8, "85f8d1b01cef926c111b194229bd6c01e2a65b18b4dd902293698e6de8f4e9ac"),
        (9, "85f8d1b01cef926c111b194229bd6c01e2a65b18b4dd902293698e6de8f4e9ac"),
    ],
)
def test_compression_levels(level: int, checksum: str) -> None:
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT), level=level)
    assert isinstance(raw, bytes)
    sha256 = hashlib.sha256(raw).hexdigest()
    assert sha256 == checksum


def test_output_file() -> None:
    data = b"rgb" * WIDTH * HEIGHT
    output = Path(f"{WIDTH}x{HEIGHT}.png")
    to_png(data, (WIDTH, HEIGHT), output=output)

    assert output.is_file()
    assert hashlib.sha256(output.read_bytes()).hexdigest() == MD5SUM


def test_output_raw_bytes() -> None:
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT))
    assert isinstance(raw, bytes)
    assert hashlib.sha256(raw).hexdigest() == MD5SUM
