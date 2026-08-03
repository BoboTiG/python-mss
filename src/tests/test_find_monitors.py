"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable

from mss import MSS
from mss.models import Monitor


def test_get_monitors(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct:
        assert sct.monitors
        assert all(isinstance(monitor, Monitor) for monitor in sct.monitors)


def test_geometry_aio(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct:
        all_monitors = sct.monitors[0]
    assert isinstance(all_monitors.top, int)
    assert isinstance(all_monitors.left, int)
    assert isinstance(all_monitors.height, int)
    assert isinstance(all_monitors.width, int)


def test_geometry_monitor_1(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct:
        mon1 = sct.monitors[1]
    assert isinstance(mon1.top, int)
    assert isinstance(mon1.left, int)
    assert isinstance(mon1.height, int)
    assert isinstance(mon1.width, int)


def test_dimensions(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct:
        mon = sct.monitors[1]
    assert mon.width > 0
    assert mon.height > 0
