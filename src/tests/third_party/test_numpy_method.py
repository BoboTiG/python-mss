"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss.screenshot import ScreenShot

np = pytest.importorskip("numpy")


def test_to_numpy_default_rgb_hwc() -> None:
    raw = bytearray([10, 20, 30, 40])
    shot = ScreenShot.from_size(raw, 1, 1)

    arr = shot.to_numpy()
    assert arr.shape == (1, 1, 3)
    assert arr.dtype == np.uint8
    assert np.array_equal(arr[0, 0], np.array([30, 20, 10], dtype=np.uint8))


def test_to_numpy_bgra_chw() -> None:
    raw = bytearray([1, 2, 3, 4])
    shot = ScreenShot.from_size(raw, 1, 1)

    arr = shot.to_numpy(channels="BGRA", layout="CHW")
    assert arr.shape == (4, 1, 1)
    assert arr.dtype == np.uint8
    assert np.array_equal(arr[:, 0, 0], np.array([1, 2, 3, 4], dtype=np.uint8))


def test_to_numpy_rgba_hwc() -> None:
    raw = bytearray([5, 6, 7, 8])
    shot = ScreenShot.from_size(raw, 1, 1)

    arr = shot.to_numpy(channels="RGBA")
    assert arr.shape == (1, 1, 4)
    assert arr.dtype == np.uint8
    assert np.array_equal(arr[0, 0], np.array([7, 6, 5, 8], dtype=np.uint8))


def test_to_numpy_bad_channels() -> None:
    raw = bytearray([0, 0, 0, 0])
    shot = ScreenShot.from_size(raw, 1, 1)

    with pytest.raises(ValueError, match="Channels must be 'BGRA', 'BGR', 'RGB', or 'RGBA'"):
        shot.to_numpy(channels="gray")  # type: ignore[arg-type]


def test_to_numpy_bad_layout() -> None:
    raw = bytearray([0, 0, 0, 0])
    shot = ScreenShot.from_size(raw, 1, 1)

    with pytest.raises(ValueError, match="Layout must be 'HWC' or 'CHW'"):
        shot.to_numpy(layout="NHWC")  # type: ignore[arg-type]
