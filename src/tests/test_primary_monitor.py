"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform
from collections.abc import Callable

import pytest

from mss import MSS
from mss.models import Monitor


def test_primary_monitor(mss_impl: Callable[..., MSS]) -> None:
    """Test that primary_monitor property works correctly."""
    with mss_impl() as sct:
        primary = sct.primary_monitor
        monitors = sct.monitors

        assert isinstance(primary, Monitor)

        # Should be in the monitors list (excluding index 0 which is "all monitors")
        assert primary in monitors[1:]

        # Should either be marked as primary or be the first monitor as fallback
        if primary.is_primary:
            assert primary.is_primary is True
        else:
            assert primary == monitors[1]


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows only")
def test_primary_monitor_coordinates_windows() -> None:
    """Test that on Windows, the primary monitor has coordinates at (0, 0)."""
    import mss  # noqa: PLC0415

    with mss.MSS() as sct:
        primary = sct.primary_monitor
        if primary.is_primary:
            # On Windows, the primary monitor is at (0, 0)
            assert primary.left == 0
            assert primary.top == 0
