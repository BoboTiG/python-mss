#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

from os import rename
from os.path import isfile

from mss import ScreenshotError, mss


def main():
    ''' Usage example. '''

    def on_exists(fname):
        ''' Callback example when we try to overwrite an existing
            screenshot.
        '''

        if isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            rename(fname, newfile)
        return True

    try:
        with mss() as screenshotter:
            # For MacOS X only
            # screenshotter.max_displays = 32

            print('One screenshot per monitor')
            for filename in screenshotter.save():
                print(filename)

            print("\nScreenshot of the monitor 1")
            print(next(screenshotter.save(mon=1, output='monitor-%d.png')))

            print("\nA screenshot to grab them all")
            print(next(screenshotter.save(mon=-1, output='fullscreen.png')))

            print("\nScreenshot of the monitor 1, with callback")
            print(next(screenshotter.save(mon=1, output='mon-%d.png',
                                          callback=on_exists)))

            return 0
    except ScreenshotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
