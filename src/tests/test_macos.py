"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import ctypes.util
import platform
from unittest.mock import patch

import pytest

import mss
from mss.exception import ScreenShotError

if platform.system().lower() != "darwin":
    pytestmark = pytest.mark.skip

import mss.darwin


def test_repr() -> None:
    # CGPoint
    point = mss.darwin.CGPoint(2.0, 1.0)
    ref1 = mss.darwin.CGPoint()
    ref1.x = 2.0
    ref1.y = 1.0
    assert repr(point) == repr(ref1)

    # CGSize
    size = mss.darwin.CGSize(2.0, 1.0)
    ref2 = mss.darwin.CGSize()
    ref2.width = 2.0
    ref2.height = 1.0
    assert repr(size) == repr(ref2)

    # CGRect
    rect = mss.darwin.CGRect(point, size)
    ref3 = mss.darwin.CGRect()
    ref3.origin.x = 2.0
    ref3.origin.y = 1.0
    ref3.size.width = 2.0
    ref3.size.height = 1.0
    assert repr(rect) == repr(ref3)


def test_implementation(monkeypatch: pytest.MonkeyPatch) -> None:
    # No `CoreGraphics` library
    version = float(".".join(platform.mac_ver()[0].split(".")[:2]))

    if version < 10.16:
        monkeypatch.setattr(ctypes.util, "find_library", lambda _: None)
        with pytest.raises(ScreenShotError):
            mss.mss()
        monkeypatch.undo()

    with mss.mss() as sct:
        assert isinstance(sct, mss.darwin.MSS)  # For Mypy

        # Test monitor's rotation
        original = sct.monitors[1]
        monkeypatch.setattr(sct.core, "CGDisplayRotation", lambda _: -90.0)
        sct._monitors = []
        modified = sct.monitors[1]
        assert original["width"] == modified["height"]
        assert original["height"] == modified["width"]
        monkeypatch.undo()

        # Test bad data retrieval
        monkeypatch.setattr(sct.core, "CGWindowListCreateImage", lambda *_: None)
        with pytest.raises(ScreenShotError):
            sct.grab(sct.monitors[1])


def test_scaling_on() -> None:
    """Screnshots are taken at the nominal resolution by default, but scaling can be turned on manually."""
    # Grab a 1x1 screenshot
    region = {"top": 0, "left": 0, "width": 1, "height": 1}

    with mss.mss() as sct:
        # Nominal resolution, i.e.: scaling is off
        assert sct.grab(region).size[0] == 1

        # Retina resolution, i.e.: scaling is on
        with patch.object(mss.darwin, "IMAGE_OPTIONS", 0):
            assert sct.grab(region).size[0] == 2
