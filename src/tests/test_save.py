"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""
import os.path
from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time
from mss import mss

try:
    from datetime import UTC
except ImportError:
    # Python < 3.11
    from datetime import timezone

    UTC = timezone.utc


FROZEN_TIME = "2024-02-21 16:35:20"


def test_at_least_2_monitors() -> None:
    with mss(display=os.getenv("DISPLAY")) as sct:
        assert list(sct.save(mon=0))


def test_files_exist() -> None:
    with mss(display=os.getenv("DISPLAY")) as sct:
        for filename in sct.save():
            assert os.path.isfile(filename)

        assert os.path.isfile(sct.shot())

        sct.shot(mon=-1, output="fullscreen.png")
        assert os.path.isfile("fullscreen.png")


def test_callback() -> None:
    def on_exists(fname: str) -> None:
        if os.path.isfile(fname):
            new_file = f"{fname}.old"
            os.rename(fname, new_file)

    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=0, output="mon0.png", callback=on_exists)
        assert os.path.isfile(filename)

        filename = sct.shot(output="mon1.png", callback=on_exists)
        assert os.path.isfile(filename)


def test_output_format_simple() -> None:
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output="mon-{mon}.png")
    assert filename == "mon-1.png"
    assert os.path.isfile(filename)


def test_output_format_positions_and_sizes() -> None:
    fmt = "sct-{top}x{left}_{width}x{height}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt)
        assert filename == fmt.format(**sct.monitors[1])
    assert os.path.isfile(filename)


def test_output_format_date_simple() -> None:
    fmt = "sct_{mon}-{date}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        try:
            filename = sct.shot(mon=1, output=fmt)
            assert os.path.isfile(filename)
        except OSError:
            # [Errno 22] invalid mode ('wb') or filename: 'sct_1-2019-01-01 21:20:43.114194.png'
            pytest.mark.xfail("Default date format contains ':' which is not allowed.")


def test_output_format_date_custom() -> None:
    fmt = "sct_{date:%Y-%m-%d}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(date=datetime.now(tz=UTC))
    assert os.path.isfile(filename)


@freeze_time(FROZEN_TIME)
def test_output_format_custom_date_function() -> None:
    def custom_date() -> datetime:
        return datetime.now(tz=UTC) + timedelta(days=6)

    fmt = "{date}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt, date_fn=custom_date)
    assert filename == "2024-02-27 16:35:20+00:00.png"
    assert os.path.isfile(filename)


@freeze_time(FROZEN_TIME)
def test_output_format_date_custom_and_custom_date_function() -> None:
    def custom_date() -> datetime:
        return datetime.now(tz=UTC) + timedelta(days=6)

    fmt = "{date:%Y-%m-%d}.png"
    with mss(display=os.getenv("DISPLAY")) as sct:
        filename = sct.shot(mon=1, output=fmt, date_fn=custom_date)
    assert filename == "2024-02-27.png"
    assert os.path.isfile(filename)
