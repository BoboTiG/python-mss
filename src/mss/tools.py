# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

import os
import struct
import zlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


_EDID_BLOCK_LEN = 128
_EDID_SERIAL_NUMBER_NOT_SET = 0  # The serial number field is unused
_EDID_MANUFACTURE_WEEK_YEAR_IS_MODEL = 0xFF  # The year field is for the model year, not the year of manufacture.
_EDID_MANUFACTURE_WEEK_UNKNOWN = 0  # Only the year of manufacture, not the week, is known.
_EDID_YEAR_BASE = 1990  # The starting year for EDID years
_EDID_DESCR_OFFSETS = [0x48, 0x5A, 0x6C]  # Display descriptor definition locations in the base block
_EDID_DESCR_LEN = 18
_EDID_DESCR_ZERO_LOCS = [0, 1, 2, 4]  # Locations that must be 0 to mark a display descriptor definition
_EDID_DESCR_TAG_LOC = 3  # Location of display descriptor tag
_EDID_DESCR_TAG_SN = 0xFF  # Descriptor is a string serial number
_EDID_DESCR_TAG_NAME = 0xFC  # Descriptor is a string model name
_EDID_DESCR_STR_LOC = slice(5, 18)  # Location of string in a display descriptor


def parse_edid(edid_data: bytes) -> dict:
    """Parse a monitor's EDID block.

    Many fields are currently ignored, but may be added in the future.

    If the EDID block cannot be parsed, this returns an empty dict.

    The dict defines the following fields.  Any of these may be
    missing, if the EDID block does not define them.

    - id_legacy (str): The legacy monitor ID, used in a number of
      APIs.  This is simply f"{manufacturer}{product_code:04X}".
      Those subfields are not part of the returned dict, but are
      nominally described as:

      - manufacturer (str): A three-letter, all-uppercase code
        specifying the manufacturer's legacy PnP ID.  The registry is
        managed by UEFI forum.
      - product_code (int): A 16-bit product code.  This is typically
        displayed as four hex digits if rendered to a string.

    - serial_number (str | int): Serial number of the monitor.  EDID
      block may provide this as an int, string, or both; the string
      version is preferred.
    - manufacture_week (int): The week, 1-54, of manufacture.  This
      may not be populated, even if the year is.  (The way the weeks
      are numbered is up to the manufacturer.)
    - manufacture_year (int): The year, 1990 or later, of manufacture.
    - model_year (int): The year, 1990 or later, that the model was
      released.  This is used if the manufacturer doesn't want to
      update their EDID block each year; the manufacture_year field is
      more common.
    - display_name (str): The monitor's model.  This is the preferred
      value for display.  If this field is not present, then id_legacy
      is a distant second.

    Currently, the serial_number and name fields are always in ASCII.
    This function doesn't currently try to implement the
    internationalization extensions defined in the VESA LS-EXT
    standard.  However, we may in the future.

    We also don't currently inspect the extension blocks.  The name
    and serial number can be in CTA-861 extension blocks; I'll need to
    see how common that is.
    """
    # See also https://glenwing.github.io/docs/ for a lot of the relevant specs.

    if len(edid_data) < _EDID_BLOCK_LEN:
        # Too short
        return {}

    # Get the basic identification information from the start of the
    # header.  This has been part of EDID for a very long time.
    block0 = edid_data[:_EDID_BLOCK_LEN]
    if sum(block0) % 256 != 0:
        # Checksum failure
        return {}

    (
        header,
        id_manufacturer_msb,
        id_manufacturer_lsb,
        id_product_code,
        id_serial_number,
        manufacture_week,
        manufacture_year,
        _edid_version,
        _edid_revision,
        _ext_count,
    ) = struct.unpack("<8s2BHIBBBB106xBx", block0)

    if header != b"\x00\xff\xff\xff\xff\xff\xff\x00":
        # Header incorrect
        return {}
    id_manufacturer_packed = id_manufacturer_msb << 8 | id_manufacturer_lsb
    id_manufacturer = (
        chr(((id_manufacturer_packed >> 10) % 32) + 64)
        + chr(((id_manufacturer_packed >> 5) % 32) + 64)
        + chr((id_manufacturer_packed % 32) + 64)
    )
    rv: dict[str, int | str] = {
        "id_legacy": f"{id_manufacturer}{id_product_code:04X}",
    }
    if id_serial_number != _EDID_SERIAL_NUMBER_NOT_SET:
        rv["serial_number"] = id_serial_number
    if manufacture_week == _EDID_MANUFACTURE_WEEK_YEAR_IS_MODEL:
        rv["model_year"] = manufacture_year + _EDID_YEAR_BASE
    else:
        if manufacture_week != _EDID_MANUFACTURE_WEEK_UNKNOWN:
            rv["manufacture_week"] = manufacture_week
        rv["manufacture_year"] = manufacture_year + _EDID_YEAR_BASE

    # Read the display descriptor definitions, which can have more useful information.
    for descr_offset in _EDID_DESCR_OFFSETS:
        descr = block0[descr_offset : descr_offset + _EDID_DESCR_LEN]
        if any(descr[field_offset] != 0 for field_offset in _EDID_DESCR_ZERO_LOCS):
            # Not a display descriptor definition
            continue
        # Check the tag in descr[3].
        # These strings are in ASCII, optionally terminated by \x0A then right-padded with \x20.  In case a
        # manufacturer got it a little wrong, we ignore everything after \x0A, and we also strip trailing \x20.  (The
        # spec requires the \x0A, but some manufacturers don't follow that.)
        if descr[_EDID_DESCR_TAG_LOC] == _EDID_DESCR_TAG_SN:  # Serial number
            sn = descr[_EDID_DESCR_STR_LOC]
            sn, _, _ = sn.partition(b"\x0a")
            sn = sn.rstrip(b" ")
            rv["serial_number"] = sn.decode("ascii", errors="replace")
        elif descr[_EDID_DESCR_TAG_LOC] == _EDID_DESCR_TAG_NAME:  # Name
            name = descr[_EDID_DESCR_STR_LOC]
            name, _, _ = name.partition(b"\x0a")
            name = name.rstrip(b" ")
            rv["display_name"] = name.decode("ascii", errors="replace")

    return rv


def to_png(data: bytes, size: tuple[int, int], /, *, level: int = 6, output: Path | str | None = None) -> bytes | None:
    """Dump data to a PNG file.  If `output` is `None`, create no file but return
    the whole PNG data.

    :param bytes data: RGBRGB...RGB data.
    :param tuple size: The (width, height) pair.
    :param int level: PNG compression level (see :py:func:`zlib.compress()` for details).
    :param str output: Output file name.

    .. versionadded:: 3.0.0

    .. versionchanged:: 3.2.0
       Added the ``level`` keyword argument to control the PNG compression level.
    """
    pack = struct.pack
    crc32 = zlib.crc32

    width, height = size
    line = width * 3
    png_filter = pack(">B", 0)
    scanlines = b"".join([png_filter + data[y * line : y * line + line] for y in range(height)])

    magic = pack(">8B", 137, 80, 78, 71, 13, 10, 26, 10)

    # Header: size, marker, data, CRC32
    ihdr = [b"", b"IHDR", b"", b""]
    ihdr[2] = pack(">2I5B", width, height, 8, 2, 0, 0, 0)
    ihdr[3] = pack(">I", crc32(b"".join(ihdr[1:3])) & 0xFFFFFFFF)
    ihdr[0] = pack(">I", len(ihdr[2]))

    # Data: size, marker, data, CRC32
    idat = [b"", b"IDAT", zlib.compress(scanlines, level), b""]
    idat[3] = pack(">I", crc32(b"".join(idat[1:3])) & 0xFFFFFFFF)
    idat[0] = pack(">I", len(idat[2]))

    # Footer: size, marker, None, CRC32
    iend = [b"", b"IEND", b"", b""]
    iend[3] = pack(">I", crc32(iend[1]) & 0xFFFFFFFF)
    iend[0] = pack(">I", len(iend[2]))

    if not output:
        # Returns raw bytes of the whole PNG data
        return magic + b"".join(ihdr + idat + iend)

    with open(output, "wb") as fileh:  # noqa: PTH123
        fileh.write(magic)
        fileh.write(b"".join(ihdr))
        fileh.write(b"".join(idat))
        fileh.write(b"".join(iend))

        # Force write of file to disk
        fileh.flush()
        os.fsync(fileh.fileno())

    return None
