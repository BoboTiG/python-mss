"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import pytest

from mss import ScreenShot
from tests.third_party.array_frameworks.conftest import reordered_test_image

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")


def test_to_torch_default() -> None:
    raw = bytearray([1, 2, 3, 4])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_torch()
    assert tuple(tensor.shape) == (3, 1, 1)
    assert tensor.dtype == torch.get_default_dtype()
    expected = torch.tensor([3 / 255.0, 2 / 255.0, 1 / 255.0], dtype=torch.float32)
    assert torch.allclose(tensor[:, 0, 0], expected)


def test_to_torch_dtype_uint8() -> None:
    raw = bytearray([5, 6, 7, 8])
    shot = ScreenShot.from_size(raw, 1, 1)

    tensor = shot.to_torch(dtype=torch.uint8)
    assert tensor.dtype == torch.uint8
    assert torch.equal(tensor[:, 0, 0], torch.tensor([7, 6, 5], dtype=torch.uint8))


@pytest.mark.parametrize("layout", ["HWC", "CHW"])
@pytest.mark.parametrize("channels", ["BGRA", "BGR", "RGBA", "RGB"])
@pytest.mark.parametrize("cuda", [False, True])
def test_to_torch_permutations(framework_test_image: ScreenShot, channels: str, layout: str, cuda: bool) -> None:
    """Test all permutations of channels and layouts."""
    if cuda and not torch.cuda.is_available():
        # The CUDA versions won't be run in CI/CD, but it's still worth checking them on developers' machines if they
        # happen to have PyTorch with CUDA support.
        pytest.skip("CUDA is not available")

    uint8_target = reordered_test_image(channels=channels, layout=layout)
    bfloat16_target = uint8_target.astype(np.float32) / 255.0

    uint8_result = framework_test_image.to_torch(
        channels=channels,  # type: ignore[arg-type]
        layout=layout,  # type: ignore[arg-type]
        dtype=torch.uint8,
        device="cuda" if cuda else "cpu",
    )
    assert uint8_result.dtype == torch.uint8
    assert np.array_equal(uint8_result.cpu().numpy(), uint8_target)

    bfloat16_result = framework_test_image.to_torch(
        channels=channels,  # type: ignore[arg-type]
        layout=layout,  # type: ignore[arg-type]
        dtype=torch.bfloat16,
        device="cuda" if cuda else "cpu",
    )
    assert bfloat16_result.dtype == torch.bfloat16
    # We have to explicitly cast back to float32 for the comparison, because PyTorch won't directly convert bfloat16 to
    # NumPy.
    bfloat16_result_f32 = bfloat16_result.to(torch.float32)
    assert np.allclose(bfloat16_result_f32.cpu().numpy(), bfloat16_target, rtol=0, atol=1 / 512.0)
