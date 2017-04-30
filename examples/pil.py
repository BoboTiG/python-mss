# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

from mss.exception import ScreenshotError
from mss.factory import mss
from PIL import Image


def main():
    # type: () -> int
    """ PIL example using frombytes(). """

    try:
        with mss() as sct:
            # We retrieve monitors informations:
            monitors = sct.enum_display_monitors()

            # Get rid of the first, as it represents the "All in One" monitor:
            for num, monitor in enumerate(monitors[1:], 1):
                # Get raw pixels from the screen.
                # This method will store screen size into `width` and `height`
                # and raw pixels into `image`.
                sct.get_pixels(monitor)

                # Create an Image
                size = (sct.width, sct.height)
                img = Image.frombytes('RGB', size, sct.image)

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
