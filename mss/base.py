# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

from struct import pack
from zlib import compress, crc32

from .exception import ScreenshotError


# C'est parti mon kiki !
class MSSBase(object):
    """ This class will be overloaded by a system specific one. """

    image = None
    width = 0
    height = 0

    def __enter__(self):
        """ For the cool call `with MSS() as mss:`. """

        return self

    def __exit__(self, *_):
        """ For the cool call `with MSS() as mss:`. """

    def bgra_to_rgb(self, raw):
        """ Converts pixels values from BGRA to RGB. """

        image = bytearray(self.height * self.width * 3)
        image[0::3], image[1::3], image[2::3] = raw[2::4], raw[1::4], raw[0::4]
        return bytes(image)

    def get_pixels(self, monitor):
        """ Retrieve screen pixels for a given monitor.

            This method has to define self.width and self.height.

            `monitor` is a dict with:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'heigth': the height
            }
        """

        raise NotImplementedError('Subclasses need to implement this!')

    @property
    def monitors(self):
        """ Get positions of all monitors.
            If the monitor has rotation, you have to deal with it
            inside this method.

            This method has to fill self.__monitors with all informations
            and use it as a cache:
                self.__monitors[0] is a dict of all monitors together
                self.__monitors[N] is a dict of the monitor N (with N > 0)

            Each monitor is a dict with:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        """

        raise NotImplementedError('Subclasses need to implement this!')

    def save(self, mon=0, output='monitor-%d.png', callback=None):
        """ Grab a screenshot and save it to a file.

            mon (integer, default: 0)
                -1: grab one screenshot of all monitors
                 0: grab one screenshot by monitor
                 N: grab the screenshot of the monitor N

            output (string, default: monitor-%d.png)
                The output filename.
                %d, if present, will be replaced by the monitor number.

            callback (method)
                Callback called before saving the screenshot to a file.
                Take the 'output' argument as parameter.

            This is a generator which returns created files.
        """

        monitors = self.monitors  # Implemented by subclasses
        if not monitors:
            raise ScreenshotError('No monitor found.')

        if mon == 0:
            # One screenshot by monitor
            for i, monitor in enumerate(monitors[1:], 1):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i))
                if callable(callback):
                    callback(fname)
                self.to_png(self.get_pixels(monitor), fname)
                yield fname
        else:
            # A screenshot of all monitors together or
            # a screenshot of the monitor N.
            mon_number = 0 if mon == -1 else mon
            try:
                monitor = monitors[mon_number]
            except IndexError:
                raise ScreenshotError('Monitor does not exist.', locals())

            if '%d' in output:
                output = output.replace('%d', str(mon_number))
            if callable(callback):
                callback(output)
            self.to_png(self.get_pixels(monitor), output)
            yield output

    def to_png(self, data, output):
        """ Dump data to the image file. Data is bytes(RGBRGB...RGB).
            Pure python PNG implementation.
            http://inaps.org/journal/comment-fonctionne-le-png
        """

        p__ = pack
        line = self.width * 3
        png_filter = p__('>B', 0)
        scanlines = b''.join(
            [png_filter + data[y * line:y * line + line]
             for y in range(self.height)])

        magic = p__('>8B', 137, 80, 78, 71, 13, 10, 26, 10)

        # Header: size, marker, data, CRC32
        ihdr = [b'', b'IHDR', b'', b'']
        ihdr[2] = p__('>2I5B', self.width, self.height, 8, 2, 0, 0, 0)
        ihdr[3] = p__('>I', crc32(b''.join(ihdr[1:3])) & 0xffffffff)
        ihdr[0] = p__('>I', len(ihdr[2]))

        # Data: size, marker, data, CRC32
        idat = [b'', b'IDAT', compress(scanlines), b'']
        idat[3] = p__('>I', crc32(b''.join(idat[1:3])) & 0xffffffff)
        idat[0] = p__('>I', len(idat[2]))

        # Footer: size, marker, None, CRC32
        iend = [b'', b'IEND', b'', b'']
        iend[3] = p__('>I', crc32(iend[1]) & 0xffffffff)
        iend[0] = p__('>I', len(iend[2]))

        with open(output, 'wb') as fileh:
            fileh.write(magic)
            fileh.write(b''.join(ihdr))
            fileh.write(b''.join(idat))
            fileh.write(b''.join(iend))
            return

    # ---------------------------------------------------------
    # DEPRECATED -- Will be removed in the next version (2.1.x)

    def enum_display_monitors(self, force=False):
        # pylint: disable=no-self-use,unused-argument,missing-docstring
        raise DeprecationWarning(
            'Deprecated since 2.1.0. Implement the `monitors` property.')
