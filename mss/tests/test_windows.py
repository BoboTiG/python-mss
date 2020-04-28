"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import platform
import threading

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

        # Grab the area 1
        region1 = {"top": 0, "left": 0, "width": 200, "height": 200}
        sct.grab(region1)
        bmp1 = id(MSS.bmp)

        # Grab the area 2, the cached BMP is used
        # Same sizes but different positions
        region2 = {"top": 200, "left": 200, "width": 200, "height": 200}
        sct.grab(region2)
        bmp2 = id(MSS.bmp)
        assert bmp1 == bmp2

        # Grab the area 2 again, the cached BMP is used
        sct.grab(region2)
        assert bmp2 == id(MSS.bmp)


def run_child_thread(loops):
    for _ in range(loops):
        with mss.mss() as sct:
            sct.grab(sct.monitors[1])


def test_thread_safety():
    """Thread safety test for issue #150.
    The following code will throw a ScreenShotError exception if thread-safety is not guaranted.
    """
    # Let thread 1 finished ahead of thread 2
    thread1 = threading.Thread(target=run_child_thread, args=(30,))
    thread2 = threading.Thread(target=run_child_thread, args=(50,))
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
