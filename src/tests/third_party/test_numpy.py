"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable

import pytest

from mss import MSS

np = pytest.importorskip("numpy", reason="Numpy module not available.")


def test_numpy(mss_impl: Callable[..., MSS]) -> None:
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    with mss_impl() as sct:
        img = np.array(sct.grab(box))
    assert len(img) == 10
