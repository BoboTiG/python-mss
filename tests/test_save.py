# coding: utf-8

import os.path
import mss


def test_at_least_2_monitors(sct):
    shots = list(sct.save(mon=0))
    assert len(shots) >= 1


def test_files_exist(sct):
    for filename in sct.save():
        assert os.path.isfile(filename)

    assert os.path.isfile(sct.shot())

    sct.shot(mon=-1, output='fullscreen.png')
    assert os.path.isfile('fullscreen.png')


def test_callback():

    def on_exists(fname):
        if os.path.isfile(fname):
            new_file = fname + '.old'
            os.rename(fname, new_file)

    with mss.mss() as sct:
        filename = sct.shot(mon=0, output='mon0.png', callback=on_exists)
        assert os.path.isfile(filename)

        filename = sct.shot(output='mon1.png', callback=on_exists)
        assert os.path.isfile(filename)
