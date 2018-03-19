# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Numpy example.
"""
import time

import numpy
from PIL import Image

import mss
import mss.tools


def rgb(im):
    return im.rgb


def numpy_flip(im):
    frame = numpy.array(im, dtype=numpy.uint8)
    return numpy.flip(frame[:, :, :3], 2).tobytes()


def numpy_slice(im):
    return numpy.array(im, dtype=numpy.uint8)[..., [2, 1, 0]].tobytes()


def pillow(im):
    return Image.frombytes('RGB', im.size, im.bgra, 'raw', 'BGRX').tobytes()


def benchmark(func):
    with mss.mss() as sct:
        m = {'top': 0, 'left': 0, 'width': 640, 'height': 480}
        count = 0
        start = time.time()

        while (time.time() - start) <= 1:
            frame = func(sct.grab(m))
            """
            filename = 'frames/{}-{}.png'.format(func.__name__, count)
            mss.tools.to_png(frame, (640, 480), output=filename)
            """
            count += 1

        return count


print('Image.frombytes:', benchmark(pillow))
print('MSS.rgb        :', benchmark(rgb))
print('Numpy flip     :', benchmark(numpy_flip))
print('Numpy slice    :', benchmark(numpy_slice))
