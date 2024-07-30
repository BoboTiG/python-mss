"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import pytest
from mss.base import ScreenShot


def test_bad_length() -> None:
    data = bytearray(b"789c626001000000ffff030000060005")
    image = ScreenShot.from_size(data, 1024, 768)
    with pytest.raises(ValueError, match="attempt to assign"):
        _ = image.rgb


def test_good_types(raw: bytes) -> None:
    image = ScreenShot.from_size(bytearray(raw), 1024, 768)
    assert isinstance(image.raw, bytearray)
    assert isinstance(image.rgb, bytes)
