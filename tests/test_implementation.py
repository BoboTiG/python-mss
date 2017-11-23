# coding: utf-8

import os
import os.path
import platform
import sys

import pytest

import mss
import mss.tools
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


def test_factory(monkeypatch):
    # Current system
    with mss.mss() as sct:
        assert isinstance(sct, MSSBase)

    # Unknown
    monkeypatch.setattr(platform, 'system', lambda: 'Chuck Norris')
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    monkeypatch.undo()

    if not PY3:
        error = exc.value[0]
    else:
        error = exc.value.args[0]
    assert error == 'System not (yet?) implemented.'


def test_python_call(monkeypatch):
    pytest.skip('Not working for now.')
    import mss.__main__
    mss.__main__.main()

    def raise_():
        raise ScreenShotError()

    monkeypatch.setattr(mss.mss, '__init__', raise_)
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()


def test_grab_with_tuple(sct):
    left = 100
    top = 100
    right = 500
    lower = 500
    width = right - left  # 400px width
    height = lower - top  # 400px height

    # PIL like
    box = (left, top, right, lower)
    im = sct.grab(box)
    assert im.size == (width, height)

    # MSS like
    box2 = {'left': left, 'top': top, 'width': width, 'height': height}
    im2 = sct.grab(box2)
    assert im.size == im2.size
    assert im.pos == im2.pos
    assert im.rgb == im2.rgb


def test_grab_with_tuple_percents(sct):
    monitor = sct.monitors[1]
    left = monitor['left'] + monitor['width'] * 5 // 100  # 5% from the left
    top = monitor['top'] + monitor['height'] * 5 // 100  # 5% from the top
    right = left + 500  # 500px
    lower = top + 500  # 500px
    width = right - left
    height = lower - top

    # PIL like
    box = (left, top, right, lower)
    im = sct.grab(box)
    assert im.size == (width, height)

    # MSS like
    box2 = {'left': left, 'top': top, 'width': width, 'height': height}
    im2 = sct.grab(box2)
    assert im.size == im2.size
    assert im.pos == im2.pos
    assert im.rgb == im2.rgb
