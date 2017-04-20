#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from mss.exception import ScreenshotError
from mss import mss


def main():
    # type: () -> int
    ''' Example to capture part of the screen. '''

    try:
        with mss() as sct:
            # The screen part to capture
            mon = {'top': 160, 'left': 160, 'width': 160, 'height': 135}

            # Create the picture
            output = 'sct-{top}x{left}_{width}x{height}.png'.format(**mon)
            sct.to_png(sct.get_pixels(mon), output)
            print(output)

            return 0
    except ScreenshotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
