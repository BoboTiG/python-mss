"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os
import os.path

import pytest

from mss import mss

pytest.importorskip("numpy", reason="Numpy module not available.")

import numpy as np  # noqa: E402


def test_numpy(pixel_ratio: int) -> None:
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    with mss(display=os.getenv("DISPLAY")) as sct:
        img = np.array(sct.grab(box))
    assert len(img) == 10 * pixel_ratio
