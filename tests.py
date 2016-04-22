#!/usr/bin/env python
# coding: utf-8

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
        screenshotter = mss()

        print('One screenshot per monitor')
        for filename in screenshotter.save():
            print(filename)

        print("\nScreenshot of the monitor 1")
        for filename in screenshotter.save(output='monitor-%d.png', screen=1):
            print(filename)

        print("\nA screenshot to grab them all")
        for filename in screenshotter.save(output='fullscreen.png', screen=-1):
            print(filename)

        print("\nScreenshot of the monitor 1, with callback")
        for filename in screenshotter.save(output='mon-%d.png',
                                           screen=1,
                                           callback=on_exists):
            print(filename)
    except ScreenshotError as ex:
        print(ex)
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
