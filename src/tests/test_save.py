"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from mss.base import MSSBase

try:
    from datetime import UTC
except ImportError:
    # Python < 3.11
    from datetime import timezone

    UTC = timezone.utc


def test_at_least_2_monitors(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        assert list(sct.save(mon=0))


def test_files_exist(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        for filename in sct.save():
            assert Path(filename).is_file()

        assert Path(sct.shot()).is_file()

        sct.shot(mon=-1, output="fullscreen.png")
        assert Path("fullscreen.png").is_file()


def test_callback(mss_impl: Callable[..., MSSBase]) -> None:
    def on_exists(fname: str) -> None:
        file = Path(fname)
        if Path(file).is_file():
            file.rename(f"{file.name}.old")

    with mss_impl() as sct:
        filename = sct.shot(mon=0, output="mon0.png", callback=on_exists)
        assert Path(filename).is_file()

        filename = sct.shot(output="mon1.png", callback=on_exists)
        assert Path(filename).is_file()


def test_output_format_simple(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        filename = sct.shot(mon=1, output="mon-{mon}.png")
    assert filename == "mon-1.png"
    assert Path(filename).is_file()


def test_output_format_positions_and_sizes(mss_impl: Callable[..., MSSBase]) -> None:
    fmt = "sct-{top}x{left}_{width}x{height}.png"
    with mss_impl() as sct:
        filename = sct.shot(mon=1, output=fmt)
        assert filename == fmt.format(**sct.monitors[1])
    assert Path(filename).is_file()


def test_output_format_date_simple(mss_impl: Callable[..., MSSBase]) -> None:
    fmt = "sct_{mon}-{date}.png"
    with mss_impl() as sct:
        try:
            filename = sct.shot(mon=1, output=fmt)
            assert Path(filename).is_file()
        except OSError:
            # [Errno 22] invalid mode ('wb') or filename: 'sct_1-2019-01-01 21:20:43.114194.png'
            pytest.mark.xfail("Default date format contains ':' which is not allowed.")


def test_output_format_date_custom(mss_impl: Callable[..., MSSBase]) -> None:
    fmt = "sct_{date:%Y-%m-%d}.png"
    with mss_impl() as sct:
        filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(date=datetime.now(tz=UTC))
    assert Path(filename).is_file()
