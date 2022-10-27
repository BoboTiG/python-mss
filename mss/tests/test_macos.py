"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import ctypes.util
import platform

import pytest

import mss
from mss.exception import ScreenShotError

if platform.system().lower() != "darwin":
    pytestmark = pytest.mark.skip


def test_repr():
    from mss.darwin import CGPoint, CGRect, CGSize

    # CGPoint
    point = CGPoint(2.0, 1.0)
    ref = CGPoint()
    ref.x = 2.0
    ref.y = 1.0
    assert repr(point) == repr(ref)

    # CGSize
    size = CGSize(2.0, 1.0)
    ref = CGSize()
    ref.width = 2.0
    ref.height = 1.0
    assert repr(size) == repr(ref)

    # CGRect
    rect = CGRect(point, size)
    ref = CGRect()
    ref.origin.x = 2.0
    ref.origin.y = 1.0
    ref.size.width = 2.0
    ref.size.height = 1.0
    assert repr(rect) == repr(ref)


def test_implementation(monkeypatch):
    # No `CoreGraphics` library
    version = float(".".join(platform.mac_ver()[0].split(".")[:2]))

    if version < 10.16:
        monkeypatch.setattr(ctypes.util, "find_library", lambda x: None)
        with pytest.raises(ScreenShotError):
            mss.mss()
        monkeypatch.undo()

    with mss.mss() as sct:
        # Test monitor's rotation
        original = sct.monitors[1]
        monkeypatch.setattr(sct.core, "CGDisplayRotation", lambda x: -90.0)
        sct._monitors = []
        modified = sct.monitors[1]
        assert original["width"] == modified["height"]
        assert original["height"] == modified["width"]
        monkeypatch.undo()

        # Test bad data retrieval
        monkeypatch.setattr(sct.core, "CGWindowListCreateImage", lambda *args: None)
        with pytest.raises(ScreenShotError):
            sct.grab(sct.monitors[1])
