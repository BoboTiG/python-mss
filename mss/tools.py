# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import struct
import zlib


def to_png(data, size, output):
    # type: (bytes, Tuple[int, int], str) -> None
    """
    Dump data to a PNG file.

    :param bytes data: RGBRGB...RGB data.
    :param tuple size: The (width, height) pair.
    :param str output: Output file name.
    """

    width, height = size
    line = width * 3
    png_filter = struct.pack('>B', 0)
    scanlines = b''.join(
        [png_filter + data[y * line:y * line + line]
         for y in range(height)])

    magic = struct.pack('>8B', 137, 80, 78, 71, 13, 10, 26, 10)

    # Header: size, marker, data, CRC32
    ihdr = [b'', b'IHDR', b'', b'']
    ihdr[2] = struct.pack('>2I5B', width, height, 8, 2, 0, 0, 0)
    ihdr[3] = struct.pack('>I', zlib.crc32(b''.join(ihdr[1:3])) & 0xffffffff)
    ihdr[0] = struct.pack('>I', len(ihdr[2]))

    # Data: size, marker, data, CRC32
    idat = [b'', b'IDAT', zlib.compress(scanlines), b'']
    idat[3] = struct.pack('>I', zlib.crc32(b''.join(idat[1:3])) & 0xffffffff)
    idat[0] = struct.pack('>I', len(idat[2]))

    # Footer: size, marker, None, CRC32
    iend = [b'', b'IEND', b'', b'']
    iend[3] = struct.pack('>I', zlib.crc32(iend[1]) & 0xffffffff)
    iend[0] = struct.pack('>I', len(iend[2]))

    with open(output, 'wb') as fileh:
        fileh.write(magic)
        fileh.write(b''.join(ihdr))
        fileh.write(b''.join(idat))
        fileh.write(b''.join(iend))
