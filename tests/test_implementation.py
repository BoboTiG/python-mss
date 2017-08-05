# coding: utf-8

import os
import os.path
import platform
import sys

import pytest

import mss
from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot


PY3 = sys.version[0] > '2'


class MSS0(MSSBase):
    """ Nothing implemented. """
    pass


class MSS1(MSSBase):
    """ Emulate no monitors. """
    @property
    def monitors(self):
        return []


class MSS2(MSSBase):
    """ Emulate one monitor. """
    @property
    def monitors(self):
        return [{'top': 0, 'left': 0, 'width': 10, 'height': 10}]


def test_incomplete_class():
    # `monitors` property not implemented
    with pytest.raises(NotImplementedError):
        for filename in MSS0().save():
            assert os.path.isfile(filename)

    # `monitors` property is empty
    with pytest.raises(ScreenShotError):
        for filename in MSS1().save():
            assert os.path.isfile(filename)

    # `grab()` not implemented
    sct = MSS2()
    with pytest.raises(NotImplementedError):
        sct.grab(sct.monitors[0])

    # Bad monitor
    with pytest.raises(ScreenShotError):
        sct.grab(sct.shot(mon=222))


def test_repr(sct):
    box = {'top': 0, 'left': 0, 'width': 10, 'height': 10}
    img = sct.grab(box)
    ref = ScreenShot(bytearray(b'42'), box)
    assert repr(img) == repr(ref)


def test_factory_basics(monkeypatch):
    # Current system
    with mss.mss() as sct:
        assert isinstance(sct, MSSBase)

    # Unknown
    monkeypatch.setattr(platform, 'system', lambda: 'Chuck Norris')
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    if not PY3:
        error = exc.value[0]
    else:
        error = exc.value.args[0]
    assert error == 'System not (yet?) implemented.'


def test_python_call():
    # __import__('mss.__main__')
    pytest.skip('Dunno how to test mss/__main__.py.')
