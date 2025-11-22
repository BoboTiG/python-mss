"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mss.tools import to_png

if TYPE_CHECKING:
    from collections.abc import Callable

    from mss.base import MSSBase

WIDTH = 10
HEIGHT = 10


def assert_is_valid_png(*, raw: bytes | None = None, file: Path | None = None) -> None:
    Image = pytest.importorskip("PIL.Image", reason="PIL module not available.")  # noqa: N806

    assert bool(Image.open(io.BytesIO(raw) if raw is not None else file).tobytes())
    try:
        Image.open(io.BytesIO(raw) if raw is not None else file).verify()
    except Exception:  # noqa: BLE001
        pytest.fail(reason="invalid PNG data")


def test_bad_compression_level(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl(compression_level=42) as sct, pytest.raises(Exception, match="Bad compression level"):
        sct.shot()


@pytest.mark.parametrize("level", range(10))
def test_compression_level(level: int) -> None:
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT), level=level)
    assert isinstance(raw, bytes)
    assert_is_valid_png(raw=raw)


def test_output_file() -> None:
    data = b"rgb" * WIDTH * HEIGHT
    output = Path(f"{WIDTH}x{HEIGHT}.png")
    to_png(data, (WIDTH, HEIGHT), output=output)
    assert output.is_file()
    assert_is_valid_png(file=output)


def test_output_raw_bytes() -> None:
    data = b"rgb" * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT))
    assert isinstance(raw, bytes)
    assert_is_valid_png(raw=raw)
