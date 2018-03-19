# coding: utf-8
"""
2018-03-19.

Maximum screenshots in 1 second by computing BGRA raw values to RGB.


GNU/Linux
  pil_frombytes 595
  mss_rgb       437
  numpy_flip    183
  numpy_slice   156

macOS
  pil_frombytes 115
  mss_rgb       108
  numpy_flip     67
  numpy_slice    65

Windows
  pil_frombytes 294
  mss_rgb       261
  numpy_flip    124
  numpy_slice   115
"""

import time

import numpy
from PIL import Image

import mss


def mss_rgb(im):
    return im.rgb


def numpy_flip(im):
    frame = numpy.array(im, dtype=numpy.uint8)
    return numpy.flip(frame[:, :, :3], 2).tobytes()


def numpy_slice(im):
    return numpy.array(im, dtype=numpy.uint8)[..., [2, 1, 0]].tobytes()


def pil_frombytes(im):
    return Image.frombytes('RGB', im.size, im.bgra, 'raw', 'BGRX').tobytes()


def benchmark(func):
    with mss.mss() as sct:
        m = {'top': 0, 'left': 0, 'width': 640, 'height': 480}
        count = 0
        start = time.time()

        while (time.time() - start) <= 1:
            frame = func(sct.grab(m))  # noqa
            count += 1

        print(func.__name__, count)


benchmark(pil_frombytes)
benchmark(mss_rgb)
benchmark(numpy_flip)
benchmark(numpy_slice)
