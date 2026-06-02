"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform

import pytest

import mss.linux


@pytest.mark.skipif(platform.system().lower() != "linux", reason="GNU/Linux compatibility checks")
def test_linux_10_1_documented_symbols_are_reexported() -> None:
    # TODO(jholveck): #493 Drop this compatibility-only re-export check after 10.x transition period.
    expected = [
        "CFUNCTIONS",
        "Display",
        "PLAINMASK",
        "XErrorEvent",
        "XFixesCursorImage",
        "XImage",
        "XRRCrtcInfo",
        "XRRModeInfo",
        "XRRScreenResources",
        "XWindowAttributes",
        "ZPIXMAP",
    ]

    for symbol in expected:
        assert hasattr(mss.linux, symbol)
