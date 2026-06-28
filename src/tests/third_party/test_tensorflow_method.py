"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss import ScreenShot
from tests.third_party.conftest import reordered_test_image

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


@pytest.mark.parametrize("layout", ["HWC", "CHW"])
@pytest.mark.parametrize("channels", ["BGRA", "BGR", "RGBA", "RGB"])
def test_to_tensorflow_permutations(framework_test_image: ScreenShot, channels: str, layout: str) -> None:
    """Test all permutations of channels and layouts."""
    uint8_target = reordered_test_image(channels=channels, layout=layout)
    bfloat16_target = uint8_target.astype(np.float32) / 255.0

    uint8_result = framework_test_image.to_tensorflow(channels=channels, layout=layout, dtype="uint8")  # type: ignore[arg-type]
    assert np.array_equal(uint8_result.numpy(), uint8_target)

    bfloat16_result = framework_test_image.to_tensorflow(channels=channels, layout=layout, dtype="bfloat16")  # type: ignore[arg-type]
    assert np.allclose(bfloat16_result.numpy(), bfloat16_target, rtol=0, atol=1 / 512.0)
