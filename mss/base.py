#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from struct import pack
from zlib import compress, crc32

from .exception import ScreenshotError


# C'est parti mon kiki !
class MSSBase(object):
    ''' This class will be overloaded by a system specific one. '''

    monitors = []
    image = None

    def __enter__(self):
        ''' For the cool call `with MSS() as mss:`. '''

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        ''' For the cool call `with MSS() as mss:`. '''

    def enum_display_monitors(self, force=False):
        ''' Get positions of one or more monitors.
            If the monitor has rotation, you have to deal with it
            inside this method.

            This method has to fill self.monitors with all informations
            and use it as a cache:
                self.monitors[0] is a dict of all monitors together
                self.monitors[N] is a dict the monitor N (with N > 0)

            Each monitor is a dict:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        '''

        raise NotImplementedError('Subclasses need to implement this!')

    def get_pixels(self, monitor):
        ''' Retrieve screen pixels for a given monitor.

            `monitor` is a dict with:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'heigth': the height
            }
        '''

        raise NotImplementedError('Subclasses need to implement this!')

    def save(self,
             output='screenshot-%d.png',
             mon=0,
             callback=lambda *x: True):
        ''' Grab a screenshot and save it to a file.

            output (str)
                The output filename.
                %d, if present, will be replaced by the monitor number.

            mon (int)
                -1: grab one screenshot of all monitors
                 0: grab one screenshot by monitor
                 N: grab the screenshot of the monitor N

            callback (def)
                In case where output already exists, call the defined callback
                function with output as parameter.

            This is a generator which returns created files.
        '''

        # Monitors screen shots!
        self.enum_display_monitors()
        for i, monitor in enumerate(self.monitors):
            if mon <= 0 or (mon > 0 and i + 1 == mon):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i + 1))
                callback(fname)
                self.to_png(data=self.get_pixels(monitor),
                            width=monitor[b'width'],
                            height=monitor[b'height'],
                            output=fname)
                yield fname

    def to_png(self, data, width, height, output):
        ''' Dump data to the image file.
            Pure python PNG implementation.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        # pylint: disable=R0201, R0914

        p__ = pack
        line = width * 3
        png_filter = p__(b'>B', 0)
        scanlines = b''.join(
            [png_filter + data[y * line:y * line + line]
             for y in range(height)])

        magic = p__(b'>8B', 137, 80, 78, 71, 13, 10, 26, 10)

        # Header: size, marker, data, CRC32
        ihdr = [b'', b'IHDR', b'', b'']
        ihdr[2] = p__(b'>2I5B', width, height, 8, 2, 0, 0, 0)
        ihdr[3] = p__(b'>I', crc32(b''.join(ihdr[1:3])) & 0xffffffff)
        ihdr[0] = p__(b'>I', len(ihdr[2]))

        # Data: size, marker, data, CRC32
        idat = [b'', b'IDAT', compress(scanlines), b'']
        idat[3] = p__(b'>I', crc32(b''.join(idat[1:3])) & 0xffffffff)
        idat[0] = p__(b'>I', len(idat[2]))

        # Footer: size, marker, None, CRC32
        iend = [b'', b'IEND', b'', b'']
        iend[3] = p__(b'>I', crc32(iend[1]) & 0xffffffff)
        iend[0] = p__(b'>I', len(iend[2]))

        with open(output, 'wb') as fileh:
            fileh.write(magic)
            fileh.write(b''.join(ihdr))
            fileh.write(b''.join(idat))
            fileh.write(b''.join(iend))
            return

        err = 'Error writing data to "{0}".'.format(output)
        raise ScreenshotError(err)
