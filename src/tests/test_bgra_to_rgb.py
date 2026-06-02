"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import ctypes

from mss.base import ScreenShot


def test_good_types(raw: bytes) -> None:
    image = ScreenShot.from_size(bytearray(raw), 1024, 768)
    assert isinstance(image.rgb, memoryview)


def test_contents() -> None:
    image = ScreenShot.from_size(b"BGRA" * 1024 * 768, 1024, 768)
    assert bytes(image.rgb) == b"RGB" * 1024 * 768


def test_ctypes_pointers_from_rgb() -> None:
    image = ScreenShot.from_size(b"BGRA" * 4, 2, 2)
    assert image.rgb.readonly is False

    rgb_array = (ctypes.c_uint8 * len(image.rgb)).from_buffer(image.rgb)
    void_ptr = ctypes.c_void_p(ctypes.addressof(rgb_array))
    uint8_ptr = ctypes.cast(void_ptr, ctypes.POINTER(ctypes.c_uint8))

    assert void_ptr.value is not None
    assert uint8_ptr[0] == ord("R")
    assert uint8_ptr[1] == ord("G")
    assert uint8_ptr[2] == ord("B")
