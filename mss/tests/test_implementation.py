"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import os
import os.path
import platform

import pytest

import mss
import mss.tools
from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot


class MSS0(MSSBase):
    """Nothing implemented."""

    pass


class MSS1(MSSBase):
    """Only `grab()` implemented."""

    def grab(self, monitor):
        pass


class MSS2(MSSBase):
    """Only `monitor` implemented."""

    @property
    def monitors(self):
        return []


@pytest.mark.parametrize("cls", [MSS0, MSS1, MSS2])
def test_incomplete_class(cls):
    with pytest.raises(TypeError):
        cls()


def test_bad_monitor(sct):
    with pytest.raises(ScreenShotError):
        sct.grab(sct.shot(mon=222))


def test_repr(sct, pixel_ratio):
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    expected_box = {
        "top": 0,
        "left": 0,
        "width": 10 * pixel_ratio,
        "height": 10 * pixel_ratio,
    }
    img = sct.grab(box)
    ref = ScreenShot(bytearray(b"42"), expected_box)
    assert repr(img) == repr(ref)


def test_factory(monkeypatch):
    # Current system
    with mss.mss() as sct:
        assert isinstance(sct, MSSBase)

    # Unknown
    monkeypatch.setattr(platform, "system", lambda: "Chuck Norris")
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    monkeypatch.undo()

    error = exc.value.args[0]
    assert error == "System 'chuck norris' not (yet?) implemented."


def test_entry_point(capsys, sct):
    from datetime import datetime

    from mss.__main__ import main

    for opt in ("-m", "--monitor"):
        main([opt, "1"])
        out, _ = capsys.readouterr()
        assert out.endswith("monitor-1.png\n")
        assert os.path.isfile("monitor-1.png")
        os.remove("monitor-1.png")

    for opt in zip(("-m 1", "--monitor=1"), ("-q", "--quiet")):
        main(opt)
        out, _ = capsys.readouterr()
        assert not out
        assert os.path.isfile("monitor-1.png")
        os.remove("monitor-1.png")

    fmt = "sct-{width}x{height}.png"
    for opt in ("-o", "--out"):
        main([opt, fmt])
        out, _ = capsys.readouterr()
        for monitor, line in zip(sct.monitors[1:], out.splitlines()):
            filename = fmt.format(**monitor)
            assert line.endswith(filename)
            assert os.path.isfile(filename)
            os.remove(filename)

    fmt = "sct_{mon}-{date:%Y-%m-%d}.png"
    for opt in ("-o", "--out"):
        main(["-m 1", opt, fmt])
        filename = fmt.format(mon=1, date=datetime.now())
        out, _ = capsys.readouterr()
        assert out.endswith(filename + "\n")
        assert os.path.isfile(filename)
        os.remove(filename)

    coordinates = "2,12,40,67"
    filename = "sct-2x12_40x67.png"
    for opt in ("-c", "--coordinates"):
        main([opt, coordinates])
        out, _ = capsys.readouterr()
        assert out.endswith(filename + "\n")
        assert os.path.isfile(filename)
        os.remove(filename)

    coordinates = "2,12,40"
    for opt in ("-c", "--coordinates"):
        main([opt, coordinates])
        out, _ = capsys.readouterr()
        assert out == "Coordinates syntax: top, left, width, height\n"


def test_grab_with_tuple(sct, pixel_ratio):
    left = 100
    top = 100
    right = 500
    lower = 500
    width = right - left  # 400px width
    height = lower - top  # 400px height

    # PIL like
    box = (left, top, right, lower)
    im = sct.grab(box)
    assert im.size == (width * pixel_ratio, height * pixel_ratio)

    # MSS like
    box2 = {"left": left, "top": top, "width": width, "height": height}
    im2 = sct.grab(box2)
    assert im.size == im2.size
    assert im.pos == im2.pos
    assert im.rgb == im2.rgb


def test_grab_with_tuple_percents(sct, pixel_ratio):
    monitor = sct.monitors[1]
    left = monitor["left"] + monitor["width"] * 5 // 100  # 5% from the left
    top = monitor["top"] + monitor["height"] * 5 // 100  # 5% from the top
    right = left + 500  # 500px
    lower = top + 500  # 500px
    width = right - left
    height = lower - top

    # PIL like
    box = (left, top, right, lower)
    im = sct.grab(box)
    assert im.size == (width * pixel_ratio, height * pixel_ratio)

    # MSS like
    box2 = {"left": left, "top": top, "width": width, "height": height}
    im2 = sct.grab(box2)
    assert im.size == im2.size
    assert im.pos == im2.pos
    assert im.rgb == im2.rgb


def test_thread_safety():
    """Regression test for issue #169."""
    import threading
    import time

    def record(check):
        """Record for one second."""

        start_time = time.time()
        while time.time() - start_time < 1:
            with mss.mss() as sct:
                sct.grab(sct.monitors[1])

        check[threading.current_thread()] = True

    checkpoint = {}
    t1 = threading.Thread(target=record, args=(checkpoint,))
    t2 = threading.Thread(target=record, args=(checkpoint,))

    t1.start()
    time.sleep(0.5)
    t2.start()

    t1.join()
    t2.join()

    assert len(checkpoint) == 2
