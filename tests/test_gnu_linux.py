# coding: utf-8

import ctypes.util
import platform
import sys

import mss
from mss.base import MSSMixin
from mss.exception import ScreenShotError

import pytest


if platform.system().lower() != "linux":
    pytestmark = pytest.mark.skip


try:
    TEXT = unicode  # Python 2
except NameError:
    TEXT = str  # Python 3
PY3 = sys.version[0] > "2"


def test_factory_systems(monkeypatch):
    """
    Here, we are testing all systems.

    Too hard to maintain the test for all platforms,
    so test only on GNU/Linux.
    """

    # GNU/Linux
    monkeypatch.setattr(platform, "system", lambda: "LINUX")
    with mss.mss() as sct:
        assert isinstance(sct, MSSMixin)
    monkeypatch.undo()

    # macOS
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()

    # Windows
    monkeypatch.setattr(platform, "system", lambda: "wInDoWs")
    with pytest.raises(ValueError):
        # wintypes.py:19: ValueError: _type_ 'v' not supported
        mss.mss()
    monkeypatch.undo()


def test_implementation(monkeypatch, is_travis):
    import mss

    # Bad `display` type
    with mss.mss(display=TEXT(":42") if is_travis else TEXT(":0")):
        pass

    with pytest.raises(ScreenShotError):
        with mss.mss(display=TEXT("0")):
            pass

    # No `DISPLAY` in envars
    monkeypatch.delenv("DISPLAY")
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass
    monkeypatch.undo()

    # No `X11` library
    x11 = ctypes.util.find_library("X11")
    monkeypatch.setattr(ctypes.util, "find_library", lambda x: None)
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass
    monkeypatch.undo()

    def find_lib(lib):
        """
        Returns None to emulate no Xrandr library.
        Returns the previous found X11 library else.

        It is a naive approach, but works for now.
        """

        if lib == "Xrandr":
            return None
        return x11

    # No `Xrandr` library
    monkeypatch.setattr(ctypes.util, "find_library", find_lib)
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass
    monkeypatch.undo()

    # Bad display data
    import mss.linux

    monkeypatch.setattr(mss.linux, "Display", lambda: None)
    with pytest.raises(TypeError):
        with mss.mss():
            pass


def test_region_out_of_monitor_bounds(is_travis):
    display = TEXT(":42") if is_travis else None
    monitor = {"left": -30, "top": 0, "width": 100, "height": 100}

    with mss.mss(display=display) as sct:
        with pytest.raises(ScreenShotError) as exc:
            assert sct.grab(monitor)

        assert str(exc.value)
        assert "retval" in exc.value.details
        assert "args" in exc.value.details

        details = sct.get_error_details()
        assert details["xerror"]
        assert isinstance(details["xerror_details"], dict)
