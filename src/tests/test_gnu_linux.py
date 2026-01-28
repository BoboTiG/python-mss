"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import builtins
import ctypes.util
import platform
from ctypes import CFUNCTYPE, POINTER, _Pointer, c_int
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, NonCallableMock, patch

import pytest

import mss
import mss.linux
import mss.linux.xcb
import mss.linux.xlib
from mss.base import MSSBase
from mss.exception import ScreenShotError

if TYPE_CHECKING:
    from collections.abc import Generator

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


@pytest.fixture(autouse=True)
def without_libraries(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> Generator[None]:
    marker = request.node.get_closest_marker("without_libraries")
    if marker is None:
        yield None
        return
    skip_find = frozenset(marker.args)
    old_find_library = ctypes.util.find_library

    def new_find_library(name: str, *args: list, **kwargs: dict[str, Any]) -> str | None:
        if name in skip_find:
            return None
        return old_find_library(name, *args, **kwargs)

    # We use a context here so other fixtures or the test itself can use .undo.
    with monkeypatch.context() as mp:
        mp.setattr(ctypes.util, "find_library", new_find_library)
        yield None


@pytest.fixture
def display() -> Generator:
    with pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=DEPTH) as vdisplay:
        yield vdisplay.new_display_var


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
    with pytest.raises((ScreenShotError, ValueError)), mss.mss(backend=backend):
        pass
    monkeypatch.undo()

    # Windows
    monkeypatch.setattr(platform, "system", lambda: "wInDoWs")
    with pytest.raises(ImportError, match="cannot import name 'WINFUNCTYPE'"), mss.mss(backend=backend):
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
    # The monkeypatch implementation of delenv seems to interact badly with some other uses of setenv, so we use a
    # monkeypatch context to isolate it a bit.
    with monkeypatch.context() as mp:
        mp.delenv("DISPLAY")
        with pytest.raises(ScreenShotError), mss.mss(backend=backend):
            pass


def test_xerror_without_details() -> None:
    # Opening an invalid display with the Xlib backend will create an XError instance, but since there was no
    # XErrorEvent, then the details won't be filled in.  Generate one.
    with pytest.raises(ScreenShotError) as excinfo, mss.mss(display=":INVALID"):
        pass

    exc = excinfo.value
    # Ensure it has no details.
    assert not exc.details
    # Ensure it can be stringified.
    str(exc)


@pytest.mark.without_libraries("xcb")
@patch("mss.linux.xlib._X11", new=None)
def test_no_xlib_library(backend: str) -> None:
    with pytest.raises(ScreenShotError), mss.mss(backend=backend):
        pass


@pytest.mark.without_libraries("xcb-randr")
@patch("mss.linux.xlib._XRANDR", new=None)
def test_no_xrandr_extension(backend: str) -> None:
    with pytest.raises(ScreenShotError), mss.mss(backend=backend):
        pass


@patch("mss.linux.xlib.MSS._is_extension_enabled", new=Mock(return_value=False))
def test_xrandr_extension_exists_but_is_not_enabled(display: str) -> None:
    with pytest.raises(ScreenShotError), mss.mss(display=display, backend="xlib"):
        pass


def test_unsupported_depth(backend: str) -> None:
    # 8-bit is normally PseudoColor.  If the order of testing the display support changes, this might raise a
    # different message; just change the match= accordingly.
    with (
        pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=8) as vdisplay,
        pytest.raises(ScreenShotError, match=r"\b8\b"),
        mss.mss(display=vdisplay.new_display_var, backend=backend) as sct,
    ):
        sct.grab(sct.monitors[1])

    # 16-bit is normally TrueColor, but still just 16 bits.
    with (
        pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=16) as vdisplay,
        pytest.raises(ScreenShotError, match=r"\b16\b"),
        mss.mss(display=vdisplay.new_display_var, backend=backend) as sct,
    ):
        sct.grab(sct.monitors[1])


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


def test_shm_available() -> None:
    """Verify that the xshmgetimage backend doesn't always fallback.

    Since this backend does an automatic fallback for certain types of
    anticipated issues, that could cause some failures to be masked.
    Ensure this isn't happening.
    """
    with (
        pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=DEPTH) as vdisplay,
        mss.mss(display=vdisplay.new_display_var, backend="xshmgetimage") as sct,
    ):
        assert isinstance(sct, mss.linux.xshmgetimage.MSS)  # For Mypy
        # The status currently isn't established as final until a grab succeeds.
        sct.grab(sct.monitors[0])
        assert sct.shm_status == mss.linux.xshmgetimage.ShmStatus.AVAILABLE


def test_shm_fallback() -> None:
    """Verify that the xshmgetimage backend falls back if MIT-SHM fails.

    The most common case when a fallback is needed is with a TCP
    connection, such as the one used with ssh relaying.  By using
    DISPLAY=localhost:99 instead of DISPLAY=:99, we connect over TCP
    instead of a local-domain socket.  This is sufficient to prevent
    MIT-SHM from completing its setup: the extension is available, but
    won't be able to attach a shared memory segment.
    """
    with (
        pyvirtualdisplay.Display(size=(WIDTH, HEIGHT), color_depth=DEPTH, extra_args=["-listen", "tcp"]) as vdisplay,
        mss.mss(display=f"localhost{vdisplay.new_display_var}", backend="xshmgetimage") as sct,
    ):
        assert isinstance(sct, mss.linux.xshmgetimage.MSS)  # For Mypy
        # Ensure that the grab call completes without exception.
        sct.grab(sct.monitors[0])
        # Ensure that it really did have to fall back; otherwise, we'd need to change how we test this case.
        assert sct.shm_status == mss.linux.xshmgetimage.ShmStatus.UNAVAILABLE


def test_exception_while_holding_memoryview(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that an exception at a particular point doesn't prevent cleanup.

    The particular point is the window when the XShmGetImage's mmapped
    buffer has a memoryview still outstanding, and the pixel data is
    being copied into a bytearray.  This can take a few milliseconds.
    """
    # Force an exception during bytearray(img_mv)
    real_bytearray = builtins.bytearray

    def boom(*args: list, **kwargs: dict[str, Any]) -> bytearray:
        # Only explode when called with the memoryview (the code path we care about).
        if len(args) > 0 and isinstance(args[0], memoryview):
            # We still need to eliminate args from the stack frame, just like the fix.
            del args, kwargs
            msg = "Boom!"
            raise RuntimeError(msg)
        return real_bytearray(*args, **kwargs)

    # We have to be careful about the order in which we catch things.  If we were to catch and discard the exception
    # before the MSS object closes, it won't trigger the bug.  That's why we have the pytest.raises outside the
    # mss.mss block.  In addition, we do as much as we can before patching bytearray, to limit its scope.
    with pytest.raises(RuntimeError, match="Boom!"), mss.mss(backend="xshmgetimage") as sct:  # noqa: PT012
        monitor = sct.monitors[0]
        with monkeypatch.context() as m:
            m.setattr(builtins, "bytearray", boom)
            sct.grab(monitor)
