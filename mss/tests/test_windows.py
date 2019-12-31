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
