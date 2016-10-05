#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from mss import mss, ScreenshotError
from PIL import Image


def main():
    ''' PIL example using frombytes(). '''

    try:
        with mss() as screenshotter:
            # We retrieve monitors informations:
            monitors = screenshotter.enum_display_monitors()

            # Get rid of the first, as it represents the "All in One" monitor:
            for num, monitor in enumerate(monitors[1:], 1):
                # Get raw pixels from the screen.
                # This method will store screen size into `width` and `height`
                # and raw pixels into `image`.
                screenshotter.get_pixels(monitor)

                # Create an Image:
                size = (screenshotter.width, screenshotter.height)
                img = Image.frombytes('RGB', size, screenshotter.image)

                # And save it!
                output = 'monitor-{0}.png'.format(num)
                img.save(output)
                print(output)

            return 0
    except ScreenshotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
