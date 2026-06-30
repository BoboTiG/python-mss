from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import mss

if TYPE_CHECKING:
    # We have a separate import for just type hints, since we don't want to import numpy in the code itself (just
    # importorskip), but type checkers don't always know about importorskip.
    import numpy as np_typehints  # noqa: ICN001

# This entire tree is skipped if NumPy isn't installed.
np = pytest.importorskip("numpy")

TEST_SIZE = (320, 240)


def reordered_test_image(channels: str, layout: str) -> np_typehints.ndarray:
    """Create a test image with particular channels and layout.

    This allows us to test all the paths of channels and layouts, to
    make sure they all work.  Restrictions on things like striding
    require special cases for some paths, so we test all the paths.
    """
    y = np.arange(TEST_SIZE[1], dtype=np.uint32)[:, None]
    x = np.arange(TEST_SIZE[0], dtype=np.uint32)[None, :]

    rv = np.zeros((TEST_SIZE[1], TEST_SIZE[0], 0), dtype=np.uint32)

    for ch in channels:
        if ch == "R":
            charr = (31 * y + 1 * x + 17) & 0xFF
        elif ch == "G":
            charr = (7 * y + 17 * x + 53) & 0xFF
        elif ch == "B":
            charr = (13 * y + 29 * x + 101) & 0xFF
        elif ch == "A":
            charr = (19 * y + 11 * x + 149) & 0xFF
        else:
            msg = f'Unexpected channel "{ch}"'
            raise ValueError(msg)
        rv = np.dstack((rv, charr))
    rv = rv.astype(np.uint8)

    source_axes = ["HWC".index(ax) for ax in layout]
    destination_axes = [0, 1, 2]
    return np.moveaxis(rv, source_axes, destination_axes)


@pytest.fixture
def framework_test_image() -> mss.ScreenShot:
    ndarray = reordered_test_image("BGRA", "HWC")
    # We need the packed buffer to be R/W, hence the extra bytearray copy.
    packed = bytearray(ndarray.tobytes())
    width, height = ndarray.shape[1], ndarray.shape[0]
    return mss.ScreenShot(packed, {"left": 0, "top": 0, "width": width, "height": height})
