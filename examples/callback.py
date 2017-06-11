# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

import os
import os.path

import mss
import mss.exception


def main():
    # type: () -> int
    """ Usage example. """

    def on_exists(fname):
        # type: (str) -> None
        """ Callback example when we try to overwrite an existing
            screenshot.
        """

        if os.path.isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            os.rename(fname, newfile)

    try:
        with mss.mss() as sct:
            # sct.max_displays = 32  # macOS only

            print('One screenshot per monitor')
            for filename in sct.save():
                print(filename)

            print("\nScreenshot of the monitor 1")
            print(next(sct.save(mon=1, output='monitor-%d.png')))

            print("\nA screenshot to grab them all")
            print(next(sct.save(mon=-1, output='fullscreen.png')))

            print("\nScreenshot of the monitor 1, with callback")
            print(next(sct.save(mon=1, output='mon-%d.png',
                                callback=on_exists)))

            return 0
    except mss.exception.ScreenShotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
