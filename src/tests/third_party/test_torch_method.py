"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss.screenshot import ScreenShot

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")


def test_to_torch_default() -> None:
    raw = bytearray([1, 2, 3, 4])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_torch()
    assert tuple(tensor.shape) == (3, 1, 1)
    assert tensor.dtype == torch.float32
    expected = torch.tensor([3 / 255.0, 2 / 255.0, 1 / 255.0], dtype=torch.float32)
    assert torch.allclose(tensor[:, 0, 0], expected)


def test_to_torch_dtype_uint8() -> None:
    raw = bytearray([5, 6, 7, 8])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_torch(dtype=torch.uint8)
    assert tensor.dtype == torch.uint8
    assert torch.equal(tensor[:, 0, 0], torch.tensor([7, 6, 5], dtype=torch.uint8))
