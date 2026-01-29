"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Callable

import pytest

from mss.base import MSSBase


def test_primary_monitor(mss_impl: Callable[..., MSSBase]) -> None:
    """Test that primary_monitor property works correctly."""
    with mss_impl() as sct:
        primary = sct.primary_monitor
        monitors = sct.monitors

        # Should return a valid monitor dict
        assert primary is not None
        assert isinstance(primary, dict)
        assert "left" in primary
        assert "top" in primary
        assert "width" in primary
        assert "height" in primary

        # Should be in the monitors list (excluding index 0 which is "all monitors")
        assert primary in monitors[1:]

        # Should either be marked as primary or be the first monitor as fallback
        if primary.get("is_primary", False):
            assert primary["is_primary"] is True
        else:
            assert primary == monitors[1]


@pytest.mark.skipif("mss.windows" not in dir(), reason="Windows only")
def test_primary_monitor_coordinates_windows() -> None:
    """Test that on Windows, the primary monitor has coordinates at (0, 0)."""
    import mss  # noqa: PLC0415

    with mss.mss() as sct:
        primary = sct.primary_monitor
        assert primary is not None
        if primary.get("is_primary", False):
            # On Windows, the primary monitor is at (0, 0)
            assert primary["left"] == 0
            assert primary["top"] == 0
