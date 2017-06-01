# coding: utf-8
"""
Simple naive benchmark to compare with:
    https://pythonprogramming.net/game-frames-open-cv-python-plays-gta-v/
"""

import time

import cv2
import numpy as np
from PIL import ImageGrab

from mss import mss


def screen_record():
    a = time.time()
    while (time.time() - a) < 1:
        last_time = time.time()
        # 800x600 windowed mode
        printscreen = np.array(ImageGrab.grab(bbox=(0, 40, 800, 640)))

        """
        cv2.imshow('window',cv2.cvtColor(printscreen, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break
        """

        print('loop took {} seconds'.format(time.time() - last_time))


def screen_record_effcient():
    sct = mss()
    # 800x600 windowed mode
    mon = {'top': 0, 'left': 40, 'width': 800, 'height': 640}

    a = time.time()
    while (time.time() - a) < 1:
        last_time = time.time()
        printscreen = np.asarray(sct.get_pixels(mon))

        """
        cv2.imshow('window', cv2.cvtColor(printscreen, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break
        """

        print('loop took {} seconds'.format(time.time() - last_time))


screen_record()
