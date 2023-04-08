"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import os.path
from datetime import datetime

import pytest

from mss import mss


def test_at_least_2_monitors():
    with mss(display=os.getenv("DISPLAY")) as sct:
        assert list(sct.save(mon=0))


def test_files_exist():
    with mss(display=os.getenv("DISPLAY")) as sct:
        for filename in sct.save():
            assert os.path.isfile(filename)

        assert os.path.isfile(sct.shot())

        sct.shot(mon=-1, output="fullscreen.png")
        assert os.path.isfile("fullscreen.png")


def test_callback():
    def on_exists(fname):
        if os.path.isfile(fname):
            new_file = f"{fname}.old"
            os.rename(fname, new_file)

    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=0, output="mon0.png", callback=on_exists)
        assert os.path.isfile(filename)

        filename = sct.shot(output="mon1.png", callback=on_exists)
        assert os.path.isfile(filename)


def test_output_format_simple():
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output="mon-{mon}.png")
    assert filename == "mon-1.png"
    assert os.path.isfile(filename)


def test_output_format_positions_and_sizes():
    fmt = "sct-{top}x{left}_{width}x{height}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt)
        assert filename == fmt.format(**sct.monitors[1])
    assert os.path.isfile(filename)


def test_output_format_date_simple():
    fmt = "sct_{mon}-{date}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        try:
            filename = sct.shot(mon=1, output=fmt)
            assert os.path.isfile(filename)
        except IOError:
            # [Errno 22] invalid mode ('wb') or filename: 'sct_1-2019-01-01 21:20:43.114194.png'
            pytest.mark.xfail("Default date format contains ':' which is not allowed.")


def test_output_format_date_custom():
    fmt = "sct_{date:%Y-%m-%d}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(date=datetime.now())
    assert os.path.isfile(filename)
