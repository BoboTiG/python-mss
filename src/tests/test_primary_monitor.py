"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable

import pytest

from mss.base import MSSBase


def test_primary_monitor_is_in_monitors_list(mss_impl: Callable[..., MSSBase]) -> None:
    """Test that the primary monitor is in the monitors list."""
    with mss_impl() as sct:
        primary = sct.primary_monitor
        monitors = sct.monitors
        assert primary is not None
        # Primary should be one of the monitors (excluding index 0 which is "all monitors")
        assert primary in monitors[1:]


def test_primary_monitor_marked_or_first(mss_impl: Callable[..., MSSBase]) -> None:
    """Test that primary_monitor returns either the marked primary or the first monitor."""
    with mss_impl() as sct:
        primary = sct.primary_monitor
        monitors = sct.monitors
        assert primary is not None

        # Either it's marked as primary, or it's the first monitor
        if primary.is_primary:
            # Should be marked as primary
            assert primary.is_primary is True
        else:
            # Should be the first monitor as fallback
            assert primary == monitors[1]


@pytest.mark.skipif("mss.windows" not in dir(), reason="Windows only")
def test_primary_monitor_coordinates_windows() -> None:
    """Test that on Windows, the primary monitor has coordinates at (0, 0)."""
    import mss  # noqa: PLC0415

    with mss.mss() as sct:
        primary = sct.primary_monitor
        assert primary is not None
        if primary.is_primary:
            # On Windows, the primary monitor is at (0, 0)
            assert primary.left == 0
            assert primary.top == 0
