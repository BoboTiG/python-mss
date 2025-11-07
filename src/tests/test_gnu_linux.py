"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform
from collections.abc import Generator
from ctypes import CFUNCTYPE, POINTER, _Pointer, c_int
from typing import Any
from unittest.mock import Mock, NonCallableMock, patch

import pytest

import mss
import mss.linux
import mss.linux.xlib
from mss.base import MSSBase
from mss.exception import ScreenShotError

pyvirtualdisplay = pytest.importorskip("pyvirtualdisplay")

PYPY = platform.python_implementation() == "PyPy"

WIDTH = 200
HEIGHT = 200
DEPTH = 24


def spy_and_patch(monkeypatch: pytest.MonkeyPatch, obj: Any, name: str) -> Mock:
    """Replace obj.name with a call-through mock and return the mock."""
    real = getattr(obj, name)
    spy = Mock(wraps=real)
    monkeypatch.setattr(obj, name, spy, raising=False)
    return spy


@pytest.fixture
def display() -> Generator:
    with pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=DEPTH) as vdisplay:
        yield vdisplay.new_display_var


@pytest.fixture(params=["xlib", "getimage"])
def backend(request) -> str:
    return request.param


def test_default_backend(display: str) -> None:
    with mss.mss(display=display) as sct:
        assert isinstance(sct, MSSBase)


@pytest.mark.skipif(PYPY, reason="Failure on PyPy")
def test_factory_systems(monkeypatch: pytest.MonkeyPatch, backend: str) -> None:
    """Here, we are testing all systems.

    Too hard to maintain the test for all platforms,
    so test only on GNU/Linux.
    """
    # GNU/Linux
    monkeypatch.setattr(platform, "system", lambda: "LINUX")
    with mss.mss(backend=backend) as sct:
        assert isinstance(sct, MSSBase)
    monkeypatch.undo()

    # macOS
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    # ValueError on macOS Big Sur
    with pytest.raises((ScreenShotError, ValueError)), mss.mss():
        pass
    monkeypatch.undo()

    # Windows
    monkeypatch.setattr(platform, "system", lambda: "wInDoWs")
    with pytest.raises(ImportError, match="cannot import name 'WINFUNCTYPE'"), mss.mss():
        pass


def test_arg_display(display: str, backend: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Good value
    with mss.mss(display=display, backend=backend):
        pass

    # Bad `display` (missing ":" in front of the number)
    with pytest.raises(ScreenShotError), mss.mss(display="0", backend=backend):
        pass

    # Invalid `display` that is not trivially distinguishable.
    with pytest.raises(ScreenShotError), mss.mss(display=":INVALID", backend=backend):
        pass

    # No `DISPLAY` in envars
    monkeypatch.delenv("DISPLAY")
    with pytest.raises(ScreenShotError), mss.mss(backend=backend):
        pass


def test_xerror_without_details() -> None:
    # Opening an invalid display with the Xlib backend will create an XError instance, but since there was no
    # XErrorEvent, then the details won't be filled in.  Generate one.
    with pytest.raises(ScreenShotError) as excinfo, mss.mss(display=":INVALID", backend="xlib"):
        pass

    exc = excinfo.value
    # Ensure it has no details.
    assert not exc.details
    # Ensure it can be stringified.
    str(exc)


@patch("mss.linux.xlib._X11", new=None)
def test_no_xlib_library() -> None:
    with pytest.raises(ScreenShotError), mss.mss(backend="xlib"):
        pass


@patch("mss.linux.xlib._XRANDR", new=None)
def test_no_xrandr_extension() -> None:
    with pytest.raises(ScreenShotError), mss.mss(backend="xlib"):
        pass


@patch("mss.linux.xlib.MSS._is_extension_enabled", new=Mock(return_value=False))
def test_xrandr_extension_exists_but_is_not_enabled(display: str) -> None:
    with pytest.raises(ScreenShotError), mss.mss(display=display, backend="xlib"):
        pass


def test_unsupported_depth(backend: str) -> None:
    with (
        pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=8) as vdisplay,
        pytest.raises(ScreenShotError),
        mss.mss(display=vdisplay.new_display_var, backend=backend) as sct,
    ):
        sct.grab(sct.monitors[1])


def test_region_out_of_monitor_bounds(display: str, backend: str) -> None:
    monitor = {"left": -30, "top": 0, "width": WIDTH, "height": HEIGHT}

    if backend == "xlib":
        assert not mss.linux.xlib._ERROR

    with mss.mss(display=display, backend=backend) as sct:
        with pytest.raises(ScreenShotError) as exc:
            sct.grab(monitor)

        assert str(exc.value)

        details = exc.value.details
        assert details
        assert isinstance(details, dict)
        if backend == "getimage":
            pytest.xfail("Error strings are not yet implemented in XCB backends")
        assert isinstance(details["error"], str)
        if backend == "xlib":
            assert not mss.linux.xlib._ERROR

    if backend == "xlib":
        assert not mss.linux.xlib._ERROR


def test__is_extension_enabled_unknown_name(display: str) -> None:
    with mss.mss(display=display, backend="xlib") as sct:
        assert isinstance(sct, mss.linux.xlib.MSS)  # For Mypy
        assert not sct._is_extension_enabled("NOEXT")


def test_fast_function_for_monitor_details_retrieval(display: str, monkeypatch: pytest.MonkeyPatch) -> None:
    with mss.mss(display=display, backend="xlib") as sct:
        assert isinstance(sct, mss.linux.xlib.MSS)  # For Mypy
        assert hasattr(sct.xrandr, "XRRGetScreenResourcesCurrent")
        fast_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResourcesCurrent")
        slow_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResources")
        screenshot_with_fast_fn = sct.grab(sct.monitors[1])

    fast_spy.assert_called()
    slow_spy.assert_not_called()

    assert set(screenshot_with_fast_fn.rgb) == {0}


def test_client_missing_fast_function_for_monitor_details_retrieval(
    display: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    with mss.mss(display=display, backend="xlib") as sct:
        assert isinstance(sct, mss.linux.xlib.MSS)  # For Mypy
        assert hasattr(sct.xrandr, "XRRGetScreenResourcesCurrent")
        # Even though we're going to delete it, we'll still create a fast spy, to make sure that it isn't somehow
        # getting accessed through a path we hadn't considered.
        fast_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResourcesCurrent")
        slow_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResources")
        # If we just delete sct.xrandr.XRRGetScreenResourcesCurrent, it will get recreated automatically by ctypes
        # the next time it's accessed.  A Mock will remember that the attribute was explicitly deleted and hide it.
        mock_xrandr = NonCallableMock(wraps=sct.xrandr)
        del mock_xrandr.XRRGetScreenResourcesCurrent
        monkeypatch.setattr(sct, "xrandr", mock_xrandr)
        assert not hasattr(sct.xrandr, "XRRGetScreenResourcesCurrent")
        screenshot_with_slow_fn = sct.grab(sct.monitors[1])

    fast_spy.assert_not_called()
    slow_spy.assert_called()

    assert set(screenshot_with_slow_fn.rgb) == {0}


def test_server_missing_fast_function_for_monitor_details_retrieval(
    display: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_xrrqueryversion_type = CFUNCTYPE(
        c_int,  # Status
        POINTER(mss.linux.xlib.Display),  # Display*
        POINTER(c_int),  # int* major
        POINTER(c_int),  # int* minor
    )

    @fake_xrrqueryversion_type
    def fake_xrrqueryversion(_dpy: _Pointer, major_p: _Pointer, minor_p: _Pointer) -> int:
        major_p[0] = 1
        minor_p[0] = 2
        return 1

    with mss.mss(display=display, backend="xlib") as sct:
        assert isinstance(sct, mss.linux.xlib.MSS)  # For Mypy
        monkeypatch.setattr(sct.xrandr, "XRRQueryVersion", fake_xrrqueryversion)
        fast_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResourcesCurrent")
        slow_spy = spy_and_patch(monkeypatch, sct.xrandr, "XRRGetScreenResources")
        screenshot_with_slow_fn = sct.grab(sct.monitors[1])

    fast_spy.assert_not_called()
    slow_spy.assert_called()

    assert set(screenshot_with_slow_fn.rgb) == {0}


def test_with_cursor(display: str, backend: str) -> None:
    with mss.mss(display=display, backend=backend) as sct:
        assert not hasattr(sct, "xfixes")
        assert not sct.with_cursor
        screenshot_without_cursor = sct.grab(sct.monitors[1])

    # 1 color: black
    assert set(screenshot_without_cursor.rgb) == {0}

    with mss.mss(display=display, backend=backend, with_cursor=True) as sct:
        if backend == "xlib":
            assert hasattr(sct, "xfixes")
        assert sct.with_cursor
        screenshot_with_cursor = sct.grab(sct.monitors[1])

    # 2 colors: black & white (default cursor is a white cross)
    assert set(screenshot_with_cursor.rgb) == {0, 255}


@patch("mss.linux.xlib._XFIXES", new=None)
def test_with_cursor_but_not_xfixes_extension_found(display: str) -> None:
    with mss.mss(display=display, backend="xlib", with_cursor=True) as sct:
        assert not hasattr(sct, "xfixes")
        assert not sct.with_cursor


def test_with_cursor_failure(display: str) -> None:
    with mss.mss(display=display, backend="xlib", with_cursor=True) as sct:
        assert isinstance(sct, mss.linux.xlib.MSS)  # For Mypy
        with (
            patch.object(sct.xfixes, "XFixesGetCursorImage", return_value=None),
            pytest.raises(ScreenShotError),
        ):
            sct.grab(sct.monitors[1])
