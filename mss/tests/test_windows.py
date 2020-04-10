"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import platform

import mss
import pytest
from mss.exception import ScreenShotError


if platform.system().lower() != "windows":
    pytestmark = pytest.mark.skip


def test_implementation(monkeypatch):
    # Test bad data retrieval
    with mss.mss() as sct:
        monkeypatch.setattr(sct.gdi32, "GetDIBits", lambda *args: 0)
        with pytest.raises(ScreenShotError):
            sct.shot()


def test_region_caching():
    """The region to grab is cached, ensure this is well-done."""
    from mss.windows import MSS

    with mss.mss() as sct:
        # Reset the current BMP
        if MSS.bmp:
            sct.gdi32.DeleteObject(MSS.bmp)
            MSS.bmp = None

        # Same sizes but different positions
        region1 = {"top": 0, "left": 0, "width": 200, "height": 200}
        # Grab the area 1
        sct.grab(region1)
        bmp1 = MSS.bmp

        region2 = {"top": 200, "left": 200, "width": 200, "height": 200}

        # Grab the area 2, the cached BMP is used
        sct.grab(region2)
        bmp2 = MSS.bmp
        assert bmp1 is bmp2

        # Grab the area 2 again, the cached BMP is used
        sct.grab(region2)
        assert bmp2 is bmp2
