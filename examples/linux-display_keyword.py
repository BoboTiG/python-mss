#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from mss.exception import ScreenshotError
from mss.linux import MSS


def main():
    # type: () -> int
    ''' Usage example with a specific display. '''

    display = ':0.0'
    print('Screenshot of display "{0}"'.format(display))

    try:
        with MSS(display=display) as sct:
            output = 'monitor{0}-%d.png'.format(display)
            for filename in sct.save(output=output):
                print(filename)

            return 0
    except ScreenshotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
