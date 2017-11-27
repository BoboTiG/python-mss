# coding: utf-8

import os.path
from datetime import datetime


def test_at_least_2_monitors(sct):
    shots = list(sct.save(mon=0))
    assert len(shots) >= 1


def test_files_exist(sct):
    for filename in sct.save():
        assert os.path.isfile(filename)

    assert os.path.isfile(sct.shot())

    sct.shot(mon=-1, output='fullscreen.png')
    assert os.path.isfile('fullscreen.png')


def test_callback(sct):

    def on_exists(fname):
        if os.path.isfile(fname):
            new_file = fname + '.old'
            os.rename(fname, new_file)

    filename = sct.shot(mon=0, output='mon0.png', callback=on_exists)
    assert os.path.isfile(filename)

    filename = sct.shot(output='mon1.png', callback=on_exists)
    assert os.path.isfile(filename)


def test_output_format(sct):
    filename = sct.shot(mon=1, output='mon-{mon}.png')
    assert filename == 'mon-1.png'
    assert os.path.isfile(filename)

    fmt = 'sct-{top}x{left}_{width}x{height}.png'
    filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(**sct.monitors[1])
    assert os.path.isfile(filename)

    fmt = 'sct_{mon}-{date}.png'
    filename = sct.shot(mon=1, output=fmt)
    assert os.path.isfile(filename)

    fmt = 'sct_{date:%Y-%m-%d}.png'
    filename = sct.shot(mon=1, output=fmt)
    assert filename == fmt.format(date=datetime.now())
    assert os.path.isfile(filename)
