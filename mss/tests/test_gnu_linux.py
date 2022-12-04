"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import ctypes.util
import os
import platform

import pytest

import mss
from mss.base import MSSBase
from mss.exception import ScreenShotError

if platform.system().lower() != "linux":
    pytestmark = pytest.mark.skip


PYPY = platform.python_implementation() == "PyPy"


@pytest.mark.skipif(PYPY, reason="Failure on PyPy")
def test_factory_systems(monkeypatch):
    """
    Here, we are testing all systems.

    Too hard to maintain the test for all platforms,
    so test only on GNU/Linux.
    """

    # GNU/Linux
    monkeypatch.setattr(platform, "system", lambda: "LINUX")
    with mss.mss() as sct:
        assert isinstance(sct, MSSBase)
    monkeypatch.undo()

    # macOS
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    with pytest.raises((ScreenShotError, ValueError)):
        # ValueError on macOS Big Sur
        mss.mss()
    monkeypatch.undo()

    # Windows
    monkeypatch.setattr(platform, "system", lambda: "wInDoWs")
    with pytest.raises(ImportError):
        # ImportError: cannot import name 'WINFUNCTYPE'
        mss.mss()


def test_arg_display(monkeypatch):
    import mss

    # Good value
    display = os.getenv("DISPLAY")
    with mss.mss(display=display):
        pass

    # Bad `display` (missing ":" in front of the number)
    with pytest.raises(ScreenShotError):
        with mss.mss(display="0"):
            pass

    # No `DISPLAY` in envars
    monkeypatch.delenv("DISPLAY")
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass


@pytest.mark.skipif(PYPY, reason="Failure on PyPy")
def test_bad_display_structure(monkeypatch):
    import mss.linux

    monkeypatch.setattr(mss.linux, "Display", lambda: None)
    with pytest.raises(TypeError):
        with mss.mss():
            pass


def test_no_xlib_library(monkeypatch):
    monkeypatch.setattr(ctypes.util, "find_library", lambda x: None)
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass


def test_no_xrandr_extension(monkeypatch):
    x11 = ctypes.util.find_library("X11")

    def find_lib_mocked(lib):
        """
        Returns None to emulate no XRANDR library.
        Returns the previous found X11 library else.

        It is a naive approach, but works for now.
        """

        return None if lib == "Xrandr" else x11

    # No `Xrandr` library
    monkeypatch.setattr(ctypes.util, "find_library", find_lib_mocked)
    with pytest.raises(ScreenShotError):
        with mss.mss():
            pass


def test_region_out_of_monitor_bounds():
    display = os.getenv("DISPLAY")
    with mss.mss(display=display) as sct:
        with pytest.raises(ScreenShotError) as exc:
            monitor = {"left": -30, "top": 0, "width": 100, "height": 100}
            assert sct.grab(monitor)

        assert str(exc.value)
        assert "retval" in exc.value.details
        assert "args" in exc.value.details

        details = sct.get_error_details()
        assert details["xerror"]
        assert isinstance(details["xerror_details"], dict)


def test_has_extension():
    display = os.getenv("DISPLAY")
    with mss.mss(display=display) as sct:
        assert sct.has_extension("RANDR")
        assert not sct.has_extension("NOEXT")
