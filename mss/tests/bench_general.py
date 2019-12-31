"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

2018-03-19.

Original means MSS 3.1.2.
Patched  means MSS 3.2.0.


GNU/Linux    Original Patched   Gain %
  grab           2618    2738    +4.58
  access_rgb     1083    1128    +4.15
  output          324     322   ------
  save            320     319   ------

macOS
  grab            524     526   ------
  access_rgb      396     406    +2.52
  output          194     195   ------
  save            193     194   ------

Windows
  grab           1280    2498   +95.16
  access_rgb      574     712   +24.04
  output          139     188   +35.25
"""

from time import time

import mss
import mss.tools


def grab(sct):
    monitor = {"top": 144, "left": 80, "width": 1397, "height": 782}
    return sct.grab(monitor)


def access_rgb(sct):
    im = grab(sct)
    return im.rgb


def output(sct, filename=None):
    rgb = access_rgb(sct)
    mss.tools.to_png(rgb, (1397, 782), output=filename)


def save(sct):
    output(sct, filename="screenshot.png")


def benchmark(func):
    count = 0
    start = time()

    with mss.mss() as sct:
        while (time() - start) % 60 < 10:
            count += 1
            func(sct)

    print(func.__name__, count)


benchmark(grab)
benchmark(access_rgb)
benchmark(output)
benchmark(save)
