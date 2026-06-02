"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import io
import struct
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mss.tools import parse_edid, to_png

if TYPE_CHECKING:
    from collections.abc import Callable

    from mss import MSS

WIDTH = 10
HEIGHT = 10


def assert_is_valid_png(*, raw: bytes | None = None, file: Path | None = None) -> None:
    Image = pytest.importorskip("PIL.Image", reason="PIL module not available.")  # noqa: N806

    assert bool(Image.open(io.BytesIO(raw) if raw is not None else file).tobytes())
    try:
        Image.open(io.BytesIO(raw) if raw is not None else file).verify()
    except Exception:  # noqa: BLE001
        pytest.fail(reason="invalid PNG data")


def test_bad_compression_level(mss_impl: Callable[..., MSS]) -> None:
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


# ---------------------------------------------------------------------------
# Helpers and tests for parse_edid
# ---------------------------------------------------------------------------


def _make_edid(  # noqa: PLR0913
    *,
    manufacturer: str = "TST",
    product_code: int = 0x1234,
    serial_number: int = 0,
    manufacture_week: int = 0,
    manufacture_year: int = 30,
    descriptors: list[tuple[int, int, str]] | None = None,
    bad_checksum: bool = False,
) -> bytes:
    """Build a minimal 128-byte EDID block."""
    data = bytearray(128)
    data[0:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"
    packed = (
        ((ord(manufacturer[0]) - ord("@")) << 10)
        | ((ord(manufacturer[1]) - ord("@")) << 5)
        | (ord(manufacturer[2]) - ord("@"))
    )
    data[8] = (packed >> 8) & 0xFF
    data[9] = packed & 0xFF
    struct.pack_into("<H", data, 10, product_code)
    struct.pack_into("<I", data, 12, serial_number)
    data[16] = manufacture_week
    data[17] = manufacture_year
    data[18] = 1  # EDID version
    data[19] = 4  # EDID revision
    _text_len = 13  # descriptor text field is 13 bytes (slice(5, 18))
    if descriptors:
        for offset, tag, text in descriptors:
            # bytes at relative offsets 0,1,2,4 must be 0 (already 0 from init)
            data[offset + 3] = tag
            encoded = text.encode("ascii")
            if len(encoded) < _text_len:
                encoded = encoded + b"\n" + b" " * (_text_len - len(encoded) - 1)
            data[offset + 5 : offset + 18] = encoded[:_text_len]
    checksum = (-sum(data[:127])) % 256
    data[127] = (checksum + 1) % 256 if bad_checksum else checksum
    return bytes(data)


def test_parse_edid_too_short() -> None:
    assert parse_edid(b"") == {}
    assert parse_edid(b"\x00" * 64) == {}
    assert parse_edid(b"\x00" * 127) == {}


def test_parse_edid_invalid_checksum() -> None:
    assert parse_edid(_make_edid(bad_checksum=True)) == {}


def test_parse_edid_invalid_header() -> None:
    data = bytearray(_make_edid())
    data[0] = 0x01  # corrupt the header magic
    data[127] = (-sum(data[:127])) % 256  # recompute checksum
    assert parse_edid(bytes(data)) == {}


def test_parse_edid_basic() -> None:
    result = parse_edid(_make_edid(manufacturer="TST", product_code=0x1234))
    assert result["id_legacy"] == "TST1234"


def test_parse_edid_manufacture_year_only() -> None:
    result = parse_edid(_make_edid(manufacture_week=0, manufacture_year=30))
    assert result["manufacture_year"] == 2020
    assert "manufacture_week" not in result
    assert "model_year" not in result


def test_parse_edid_manufacture_week_and_year() -> None:
    result = parse_edid(_make_edid(manufacture_week=10, manufacture_year=30))
    assert result["manufacture_year"] == 2020
    assert result["manufacture_week"] == 10
    assert "model_year" not in result


def test_parse_edid_model_year() -> None:
    result = parse_edid(_make_edid(manufacture_week=0xFF, manufacture_year=31))
    assert result["model_year"] == 2021
    assert "manufacture_year" not in result
    assert "manufacture_week" not in result


def test_parse_edid_serial_number_integer() -> None:
    result = parse_edid(_make_edid(serial_number=12345))
    assert result["serial_number"] == 12345


def test_parse_edid_serial_number_not_set() -> None:
    result = parse_edid(_make_edid(serial_number=0))
    assert "serial_number" not in result


def test_parse_edid_descriptor_serial_number() -> None:
    result = parse_edid(_make_edid(descriptors=[(0x48, 0xFF, "SN123456")]))
    assert result["serial_number"] == "SN123456"


def test_parse_edid_descriptor_display_name() -> None:
    result = parse_edid(_make_edid(descriptors=[(0x5A, 0xFC, "Test Monitor")]))
    assert result["display_name"] == "Test Monitor"


def test_parse_edid_descriptor_string_serial_overrides_integer() -> None:
    result = parse_edid(_make_edid(serial_number=99, descriptors=[(0x48, 0xFF, "STRSERIAL")]))
    assert result["serial_number"] == "STRSERIAL"
