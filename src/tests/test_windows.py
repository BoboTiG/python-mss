"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import ctypes

import pytest

import mss
from mss.exception import ScreenShotError
from tests.thread_helpers import run_threads

try:
    import mss.windows
    from mss.windows.gdi import MSSImplGdi, _check_result, _check_result_with_last_error
except ImportError:
    pytestmark = pytest.mark.skip


def test_choose_impl_unknown_backend_raises() -> None:
    """``choose_impl()`` must reject backends that are not registered in ``BACKENDS``."""
    bogus = "definitely-not-a-real-backend"

    with pytest.raises(ScreenShotError, match=bogus):
        mss.windows.choose_impl(backend=bogus)


def test_factory_gdi_backend() -> None:
    """``mss.MSS()`` and ``mss.MSS(backend="gdi")`` must select the GDI backend on Windows."""
    with mss.MSS() as default_sct, mss.MSS(backend="gdi") as gdi_sct:
        assert type(default_sct._impl) is MSSImplGdi
        assert type(gdi_sct._impl) is MSSImplGdi


def test_check_result_with_last_error_zero_is_not_reported_as_success() -> None:
    """A failed Windows API call may leave ``GetLastError()`` set to 0."""

    def fake_func() -> int:
        return 0

    previous_last_error = ctypes.get_last_error()
    try:
        ctypes.set_last_error(0)
        with pytest.raises(ScreenShotError, match="returned failure but no last-error code was available") as exc:
            _check_result_with_last_error(0, fake_func, ())
    finally:
        ctypes.set_last_error(previous_last_error)

    assert exc.value.details["error_code"] == 0
    assert exc.value.details["error_msg"] == (
        "The function returned a failure value, but no Windows last-error code was available."
    )


def test_check_result_with_last_error_reports_error_code() -> None:
    """A failed Windows API call should report a non-zero ``GetLastError()`` value."""

    def fake_func() -> int:
        return 0

    error_code = 8
    previous_last_error = ctypes.get_last_error()
    try:
        ctypes.set_last_error(error_code)
        with pytest.raises(ScreenShotError, match="Windows graphics function failed: fake_func:") as exc:
            _check_result_with_last_error(0, fake_func, ())
    finally:
        ctypes.set_last_error(previous_last_error)

    assert exc.value.details["func"] == "fake_func"
    assert exc.value.details["args"] == ()
    assert exc.value.details["error_code"] == error_code
    assert exc.value.details["error_msg"]
    assert isinstance(exc.value.__cause__, OSError)
    assert exc.value.__cause__.winerror == error_code


def test_check_result_ignores_stale_last_error() -> None:
    """Some Windows APIs do not document ``GetLastError()`` diagnostics."""

    def fake_func() -> None:
        pass

    previous_last_error = ctypes.get_last_error()
    try:
        ctypes.set_last_error(8)
        with pytest.raises(ScreenShotError, match="Windows graphics function returned failure: fake_func") as exc:
            _check_result(0, fake_func, ())
    finally:
        ctypes.set_last_error(previous_last_error)

    assert exc.value.details == {
        "func": "fake_func",
        "args": (),
        "error_msg": "The function returned a failure value.",
    }


def test_region_caching() -> None:
    """The region to grab is cached, ensure this is well-done."""
    with mss.MSS() as sct:
        assert isinstance(sct, mss.MSS)
        assert isinstance(sct._impl, MSSImplGdi)

        # Grab the area 1
        region1 = {"top": 0, "left": 0, "width": 200, "height": 200}
        sct.grab(region1)
        dib1 = id(sct._impl._dib)

        # Grab the area 2, the cached DIB is used
        # Same sizes but different positions
        region2 = {"top": 200, "left": 200, "width": 200, "height": 200}
        sct.grab(region2)
        dib2 = id(sct._impl._dib)
        assert dib1 == dib2

        # Grab the area 2 again, the cached DIB is used
        sct.grab(region2)
        assert dib2 == id(sct._impl._dib)


def test_region_not_caching() -> None:
    """The region to grab is not bad cached previous grab."""
    grab1 = mss.MSS()
    grab2 = mss.MSS()

    assert isinstance(grab1, mss.MSS)  # For Mypy
    assert isinstance(grab2, mss.MSS)  # For Mypy
    assert isinstance(grab1._impl, MSSImplGdi)
    assert isinstance(grab2._impl, MSSImplGdi)

    region1 = {"top": 0, "left": 0, "width": 100, "height": 100}
    region2 = {"top": 0, "left": 0, "width": 50, "height": 1}
    grab1.grab(region1)
    dib1 = id(grab1._impl._dib)
    grab2.grab(region2)
    dib2 = id(grab2._impl._dib)
    assert dib1 != dib2

    # Grab the area 1, is not bad cached DIB previous grab the area 2
    grab1.grab(region1)
    dib1 = id(grab1._impl._dib)
    assert dib1 != dib2


def test_monitors_work_when_getwindowdc_fails() -> None:
    """Regression test for issue #509.

    ``GetWindowDC(0)`` can fail (locked screen, UAC, RDP, GDI pressure).
    Enumerating monitors must still work because it only needs
    ``EnumDisplayMonitors`` / ``GetMonitorInfoW``.
    """
    with mss.MSS() as sct:
        impl = sct._impl
        assert isinstance(impl, MSSImplGdi)

        # Simulate GetWindowDC failing — grab() should raise, but
        # monitors must remain accessible.
        original = impl.user32.GetWindowDC
        impl.user32.GetWindowDC = lambda _hwnd: 0  # type: ignore[attr-defined]
        try:
            monitors = sct.monitors
            assert len(monitors) >= 1
            assert "width" in monitors[0]

            with pytest.raises(ScreenShotError):
                sct.grab(monitors[1])
        finally:
            impl.user32.GetWindowDC = original  # type: ignore[attr-defined]


def run_child_thread(loops: int) -> None:
    for _ in range(loops):
        with mss.MSS() as sct:  # New sct for every loop
            sct.grab(sct.monitors[1])


def test_thread_safety() -> None:
    """Thread safety test for issue #150.

    The following code will throw a ScreenShotError exception if thread-safety is not guaranteed.
    """
    # Let thread 1 finished ahead of thread 2
    run_threads(lambda: run_child_thread(30), lambda: run_child_thread(50))


def run_child_thread_bbox(loops: int, bbox: tuple[int, int, int, int]) -> None:
    with mss.MSS() as sct:  # One sct for all loops
        for _ in range(loops):
            sct.grab(bbox)


def test_thread_safety_regions() -> None:
    """Thread safety test for different regions.

    The following code will throw a ScreenShotError exception if thread-safety is not guaranteed.
    """
    run_threads(
        lambda: run_child_thread_bbox(100, (0, 0, 100, 100)),
        lambda: run_child_thread_bbox(100, (0, 0, 50, 1)),
    )
