# coding: utf-8

import hashlib
import os.path

from mss.tools import to_png


WIDTH = 10
HEIGHT = 10
MD5SUM = '055e615b74167c9bdfea16a00539450c'


def test_output_file():
    data = b'rgb' * WIDTH * HEIGHT
    output = '{}x{}.png'.format(WIDTH, HEIGHT)
    to_png(data, (WIDTH, HEIGHT), output=output)

    assert os.path.isfile(output)
    with open(output, 'rb') as png:
        assert hashlib.md5(png.read()).hexdigest() == MD5SUM


def test_output_raw_bytes():
    data = b'rgb' * WIDTH * HEIGHT
    raw = to_png(data, (WIDTH, HEIGHT))
    assert hashlib.md5(raw).hexdigest() == MD5SUM
