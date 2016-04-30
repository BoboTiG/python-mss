#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from mss import ScreenshotError
from mss.linux import MSS


def main():
    ''' Usage example with specified display. '''

    display = b':0.0'
    try:
        with MSS(display=display) as screenshotter:
            print('Screenshot of display "{0}"'.format(display))
            output = 'monitor{0}-%d.png'.format(display)
            for filename in screenshotter.save(output=output):
                print(filename)

            return 0
    except ScreenshotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
