"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import os

from mss import mss


def test_get_monitors():
    with mss(display=os.getenv("DISPLAY")) as sct:
        assert sct.monitors


def test_keys_aio():
    with mss(display=os.getenv("DISPLAY")) as sct:
        all_monitors = sct.monitors[0]
    assert "top" in all_monitors
    assert "left" in all_monitors
    assert "height" in all_monitors
    assert "width" in all_monitors


def test_keys_monitor_1():
    with mss(display=os.getenv("DISPLAY")) as sct:
        mon1 = sct.monitors[1]
    assert "top" in mon1
    assert "left" in mon1
    assert "height" in mon1
    assert "width" in mon1


def test_dimensions():
    with mss(display=os.getenv("DISPLAY")) as sct:
        mon = sct.monitors[1]
    assert mon["width"] > 0
    assert mon["height"] > 0
