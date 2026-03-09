"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss.screenshot import ScreenShot

np = pytest.importorskip("numpy")
tf = pytest.importorskip("tensorflow")


def test_to_tensorflow_default() -> None:
    raw = bytearray([1, 2, 3, 4])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_tensorflow()
    assert tuple(tensor.shape) == (1, 1, 3)
    assert tensor.dtype == tf.float32
    np.testing.assert_allclose(
        tensor.numpy()[0, 0],
        np.array([3.0 / 255.0, 2.0 / 255.0, 1.0 / 255.0], dtype=np.float32),
        rtol=1e-6,
        atol=1e-7,
    )


def test_to_tensorflow_dtype_string() -> None:
    raw = bytearray([9, 8, 7, 6])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_tensorflow(dtype="uint8")
    assert tensor.dtype == tf.uint8
    assert (tensor.numpy()[0, 0] == [7, 8, 9]).all()
