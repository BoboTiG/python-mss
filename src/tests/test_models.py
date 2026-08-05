"""Tests for public data models."""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError

import pytest

from mss.models import Monitor


def test_monitor() -> None:
    monitor = Monitor(
        left=1,
        top=2,
        width=3,
        height=4,
        is_primary=True,
        name="Display",
        unique_id="display-id",
        output="DP-1",
    )

    assert (monitor.left, monitor.top, monitor.width, monitor.height) == (1, 2, 3, 4)
    assert monitor.is_primary is True
    assert monitor.name == "Display"
    assert monitor.unique_id == "display-id"
    assert monitor.output == "DP-1"
    assert monitor.as_region() == {"left": 1, "top": 2, "width": 3, "height": 4}
    assert not isinstance(monitor, Mapping)
    assert not hasattr(monitor, "__dict__")

    with pytest.raises(FrozenInstanceError):
        monitor.width = 5  # type: ignore[misc]


def test_monitor_string_key_access() -> None:
    monitor = Monitor(
        left=1,
        top=2,
        width=3,
        height=4,
        is_primary=True,
        name="Display",
        unique_id="display-id",
        output="DP-1",
    )

    assert monitor["left"] == monitor.left
    assert monitor["top"] == monitor.top
    assert monitor["width"] == monitor.width
    assert monitor["height"] == monitor.height
    assert monitor["is_primary"] == monitor.is_primary
    assert monitor["name"] == monitor.name
    assert monitor["unique_id"] == monitor.unique_id
    assert monitor["output"] == monitor.output

    with pytest.raises(KeyError):
        monitor["unknown"]


def test_monitor_optional_metadata_defaults_to_none() -> None:
    monitor = Monitor(left=1, top=2, width=3, height=4)

    assert monitor.is_primary is None
    assert monitor.name is None
    assert monitor.unique_id is None
    assert monitor.output is None
