#!/usr/bin/env python
# coding: utf-8

''' Fichier test pour IndexError::Swap.efficient().

    Usage : python2 test-raw-windows.py
            python3 test-raw-windows.py

    `pixels` est rapatrié depuis test-windows.raw et casté sous
    son bon type afin d'être dans la situation exacte du
    module MSS.

    to_png() ne peut être modifiée car elle fonctionne tel
    quel pour GNU/Linux aussi. Sauf si une optimisation est
    possible, je pense notament à la création de `scanlines`.

    Le fichier data-windows.raw se trouve à l'adresse :
    https://raw.githubusercontent.com/BoboTiG/python-mss/develop/test/data-windows.raw
'''

from __future__ import print_function, unicode_literals

from ctypes import cast, c_char, POINTER
from os.path import isfile
from time import time
from struct import pack
from sys import argv, exit
from zlib import compress, crc32

def to_png(data, width, height, output):
    ''' Copied from MSS.to_png(). '''

    len_sl = (width * 3 + 3) & -4
    padding = 0 if len_sl % 8 == 0 else (len_sl % 8) // 2
    scanlines = b''.join(
        [b'0' + data[y * len_sl:y * len_sl + len_sl - padding]
         for y in range(height)])
    zcrc32 = crc32
    zcompr = compress
    b = pack

    magic = b(b'>8B', 137, 80, 78, 71, 13, 10, 26, 10)

    # Header: size, marker, data, CRC32
    ihdr = [b'', b'IHDR', b'', b'']
    ihdr[2] = b(b'>2I5B', width, height, 8, 2, 0, 0, 0)
    ihdr[3] = b(b'>I', zcrc32(b''.join(ihdr[1:3])) & 0xffffffff)
    ihdr[0] = b(b'>I', len(ihdr[2]))

    # Data: size, marker, data, CRC32
    idat = [b'', b'IDAT', b'', b'']
    idat[2] = zcompr(scanlines)
    idat[3] = b(b'>I', zcrc32(b''.join(idat[1:3])) & 0xffffffff)
    idat[0] = b(b'>I', len(idat[2]))

    # Footer: size, marker, None, CRC32
    iend = [b'', b'IEND', b'', b'']
    iend[3] = b(b'>I', zcrc32(iend[1]) & 0xffffffff)
    iend[0] = b(b'>I', len(iend[2]))

    with open(output, 'wb') as fileh:
        fileh.write(
            magic + b''.join(ihdr) + b''.join(idat) + b''.join(iend))


def to_rgb(pixels, buffer_len):
    for i in xrange(0, buffer_len - 2, 3):
        yield pixels[i + 2]
        yield pixels[i + 1]
        yield pixels[i]


width, height = 1280, 929
raw = 'data-windows.raw'
output = '{0}.png'.format(raw)

if not isfile(raw):
    print('{0} requis:'.format(raw))
    print('https://raw.githubusercontent.com/BoboTiG/python-mss/develop/test/{0}'.format(raw))
    exit(1)

with open(raw, 'rb') as fileh:
    data = fileh.read()
    buffer_len = len(data)
    pixels = cast(data, POINTER(c_char * buffer_len)).contents

    xrange = getattr(__builtins__, 'xrange', range)  # xrange pour toute version

    # Ici, on inverse le B et le R
    start = time()

    # Version 0
    # Fonctionne sous Python 2 et 3, lente.
    #for idx in xrange(0, buffer_len - 2, 3):
    #    pixels[idx + 2], pixels[idx] = pixels[idx], pixels[idx + 2]

    # Version 1
    # Fonctionne sous Python 2 et 3, rapide.
    pixels[2:buffer_len:3], pixels[0:buffer_len:3] = pixels[0:buffer_len:3], pixels[2:buffer_len:3]

    # Version 2
    # Fonctionne sous Python 2 et 3, lente.
    #pixels = b''.join(to_rgb(pixels, buffer_len))

    # Version 3
    # Ne fonctionne pas.
    #pixels = str(to_rgb(pixels, buffer_len))

    # Garde fou
    if len(pixels) != buffer_len:
        print('Erreur lors du swap BGR -> RGB.')
        exit(1)

    print(time() - start)

    # Enregistrement de l'image
    to_png(pixels, width, height, output)
