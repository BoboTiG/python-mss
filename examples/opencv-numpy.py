# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

import time

import cv2
import mss
import mss.exception
import numpy


def main():
    # type: () -> int
    """ OpenCV/Numpy example. """

    try:
        with mss.mss() as sct:
            # Part of the screen to capture
            monitor = {'top': 40, 'left': 0, 'width': 800, 'height': 640}

            while True:
                t = time.time()

                # Get raw pixels from the screen, save it to a Numpy array
                img = numpy.array(sct.grab(monitor))

                # Display the picture
                cv2.imshow('OpenCV/Numpy normal', img)

                # Display the picture in grayscale
                # cv2.imshow('OpenCV/Numpy grayscale',
                #            cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY))

                print('fps: {}'.format(1 / (time.time()-t)))

                # Press "q" to quit
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    cv2.destroyAllWindows()
                    break

            return 0
    except mss.exception.ScreenShotError as ex:
        print(ex)

    return 1


if __name__ == '__main__':
    exit(main())
