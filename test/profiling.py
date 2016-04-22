#!/usr/bin/env python
# coding: utf-8
''' Profiling each MSS methods.

    Needs the latest MSS developement version:
    https://github.com/BoboTiG/python-mss/tree/develop

    $ git clone https://github.com/BoboTiG/python-mss.git
    $ cd python-mss
    $ git checkout develop
    $ python setup.py install
'''

from contextlib import contextmanager
from mss import mss
from time import time


@contextmanager
def timer(msg):
    ''' A little timer. '''
    start = time()
    yield
    print('{0}: {1} s'.format(msg, time() - start))


def screenshot(screenshotter, monitor, screen):
    width = monitor[b'width']
    height = monitor[b'height']
    if screen == -1:
        print('All monitors')
        output = 'all-monitors.png'
    else:
        print('Monitor {0}'.format(screen + 1))
        output = 'monitor-{0}.png'.format(screen + 1)
    print('  {0}x{1}'.format(width, height))
    with timer('    get_pixels'):
        pixels = screenshotter.get_pixels(monitor)
    with timer('    to_png'):
        screenshotter.to_png(pixels, width, height, output)


if __name__ == '__main__':
    screenshotter = mss()
    monitors = screenshotter.enum_display_monitors(screen=0)
    for i, monitor in enumerate(monitors):
        screenshot(screenshotter, monitor, i)
    if i > 0:
        all_monitors = screenshotter.enum_display_monitors(screen=-1)
        for monitor in all_monitors:
            screenshot(screenshotter, monitor, -1)
