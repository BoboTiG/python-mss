# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

import mss
import mss.exception
import mss.tools


def main():
    # type: () -> int
    """ Example to capture part of the screen. """

    try:
        with mss.mss() as sct:
            # The screen part to capture
            monitor = {'top': 160, 'left': 160, 'width': 160, 'height': 135}

            # Save the picture
            output = 'sct-{top}x{left}_{width}x{height}.png'.format(**monitor)
            sct_img = sct.grab(monitor)
            mss.tools.to_png(sct_img.rgb, sct_img.size, output)
            print(output)

            return 0
    except mss.exception.ScreenShotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
