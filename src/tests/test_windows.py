"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import threading

import pytest

import mss
from mss.exception import ScreenShotError

try:
    import mss.windows
except ImportError:
    pytestmark = pytest.mark.skip


def test_choose_impl_unknown_backend_raises() -> None:
    """``choose_impl()`` must reject backends that are not registered in ``BACKENDS``."""
    bogus = "definitely-not-a-real-backend"

    with pytest.raises(ScreenShotError, match=bogus):
        mss.windows.choose_impl(backend=bogus)


def test_region_caching() -> None:
    """The region to grab is cached, ensure this is well-done."""
    with mss.MSS() as sct:
        assert isinstance(sct, mss.MSS)
        assert isinstance(sct._impl, mss.windows.MSSImplWindows)

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
    assert isinstance(grab1._impl, mss.windows.MSSImplWindows)
    assert isinstance(grab2._impl, mss.windows.MSSImplWindows)

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


def run_child_thread(loops: int) -> None:
    for _ in range(loops):
        with mss.MSS() as sct:  # New sct for every loop
            sct.grab(sct.monitors[1])


def test_thread_safety() -> None:
    """Thread safety test for issue #150.

    The following code will throw a ScreenShotError exception if thread-safety is not guaranteed.
    """
    # Let thread 1 finished ahead of thread 2
    thread1 = threading.Thread(target=run_child_thread, args=(30,))
    thread2 = threading.Thread(target=run_child_thread, args=(50,))
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()


def run_child_thread_bbox(loops: int, bbox: tuple[int, int, int, int]) -> None:
    with mss.MSS() as sct:  # One sct for all loops
        for _ in range(loops):
            sct.grab(bbox)


def test_thread_safety_regions() -> None:
    """Thread safety test for different regions.

    The following code will throw a ScreenShotError exception if thread-safety is not guaranteed.
    """
    thread1 = threading.Thread(target=run_child_thread_bbox, args=(100, (0, 0, 100, 100)))
    thread2 = threading.Thread(target=run_child_thread_bbox, args=(100, (0, 0, 50, 1)))
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
