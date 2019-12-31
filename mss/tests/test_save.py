"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import os.path
from datetime import datetime

import pytest


def test_at_least_2_monitors(sct):
    shots = list(sct.save(mon=0))
    assert len(shots) >= 1


def test_files_exist(sct):
    for filename in sct.save():
        assert os.path.isfile(filename)

    assert os.path.isfile(sct.shot())

    sct.shot(mon=-1, output="fullscreen.png")
    assert os.path.isfile("fullscreen.png")


def test_callback(sct):
    def on_exists(fname):
        if os.path.isfile(fname):
            new_file = fname + ".old"
            os.rename(fname, new_file)

    filename = sct.shot(mon=0, output="mon0.png", callback=on_exists)
    assert os.path.isfile(filename)

    filename = sct.shot(output="mon1.png", callback=on_exists)
    assert os.path.isfile(filename)


def test_output_format_simple(sct):
    filename = sct.shot(mon=1, output="mon-{mon}.png")
    assert filename == "mon-1.png"
    assert os.path.isfile(filename)


def test_output_format_positions_and_sizes(sct):
    fmt = "sct-{top}x{left}_{width}x{height}.png"
    filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(**sct.monitors[1])
    assert os.path.isfile(filename)


def test_output_format_date_simple(sct):
    fmt = "sct_{mon}-{date}.png"
    try:
        filename = sct.shot(mon=1, output=fmt)
    except IOError:
        # [Errno 22] invalid mode ('wb') or filename: 'sct_1-2019-01-01 21:20:43.114194.png'
        pytest.mark.xfail("Default date format contains ':' which is not allowed.")
    else:
        assert os.path.isfile(filename)


def test_output_format_date_custom(sct):
    fmt = "sct_{date:%Y-%m-%d}.png"
    filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(date=datetime.now())
    assert os.path.isfile(filename)
