"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from mss.base import ScreenShot


def test_good_types(raw: bytes) -> None:
    image = ScreenShot.from_size(bytearray(raw), 1024, 768)
    assert isinstance(image.rgb, memoryview)
    assert image.rgb.readonly


def test_contents() -> None:
    image = ScreenShot.from_size(b"BGRA" * 1024 * 768, 1024, 768)
    assert bytes(image.rgb) == b"RGB" * 1024 * 768
