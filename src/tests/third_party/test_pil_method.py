"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss.screenshot import ScreenShot

pytest.importorskip("PIL.Image")


def test_to_pil_rgb_default() -> None:
    # The raw format is BGRA/BGRX (B, G, R, X)
    raw = bytearray([1, 2, 3, 4])
    shot = ScreenShot.from_size(raw, 1, 1)

    img = shot.to_pil()
    assert img.mode == "RGB"
    assert img.size == shot.size
    assert img.getpixel((0, 0)) == (3, 2, 1)


def test_to_pil_rgba() -> None:
    raw = bytearray([5, 6, 7, 8])
    shot = ScreenShot.from_size(raw, 1, 1)

    img = shot.to_pil("rgba")
    assert img.mode == "RGBA"
    assert img.size == shot.size
    assert img.getpixel((0, 0)) == (7, 6, 5, 8)


def test_to_pil_bad_mode() -> None:
    raw = bytearray([0, 0, 0, 0])
    shot = ScreenShot.from_size(raw, 1, 1)

    with pytest.raises(ValueError, match="Mode must be 'RGB' or 'RGBA'"):
        shot.to_pil("L")
