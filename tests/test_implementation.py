# coding: utf-8

import ctypes.util
import os
import os.path
import platform
import sys

import pytest

import mss
from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot

try:
    import numpy
except ImportError:
    numpy = None

try:
    from PIL import Image
except ImportError:
    Image = None


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


@pytest.mark.skipif(
    platform.system().lower() != 'darwin',
    reason='Specific to macOS.')
def test_repr():
    from mss.darwin import CGSize, CGPoint, CGRect

    point = CGPoint(2.0, 1.0)
    ref = CGPoint()
    ref.x = 2.0
    ref.y = 1.0
    assert repr(point) == repr(ref)

    size = CGSize(2.0, 1.0)
    ref = CGSize()
    ref.width = 2.0
    ref.height = 1.0
    assert repr(size) == repr(ref)

    rect = CGRect(point, size)
    ref = CGRect()
    ref.origin.x = 2.0
    ref.origin.y = 1.0
    ref.size.width = 2.0
    ref.size.height = 1.0
    assert repr(rect) == repr(ref)


@pytest.mark.skipif(
    numpy is None,
    reason='Numpy module not available.')
def test_numpy(sct):
    box = {'top': 0, 'left': 0, 'width': 10, 'height': 10}
    img = numpy.array(sct.grab(box))
    assert len(img) == 10


@pytest.mark.skipif(
    Image is None,
    reason='PIL module not available.')
def test_pil(sct):
    box = {'top': 0, 'left': 0, 'width': 10, 'height': 10}
    sct_img = sct.grab(box)

    img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
    assert img.mode == 'RGB'
    assert img.size == sct_img.size

    for x in range(10):
        for y in range(10):
            assert img.getpixel((x, y)) == sct_img.pixel(x, y)

    img.save('box.png')
    assert os.path.isfile('box.png')


def test_factory_basics(monkeypatch):
    # Current system
    sct = mss.mss()
    assert isinstance(sct, MSSBase)

    # Unknown
    monkeypatch.setattr(platform, 'system', lambda: 'Chuck Norris')
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    assert exc.value[0] == 'System not (yet?) implemented.'


@pytest.mark.skipif(
    platform.system().lower() != 'linux',
    reason='Too hard to maintain the test for all platforms.')
def test_factory_systems(monkeypatch):
    """ Here, we are testing all systems. """

    # GNU/Linux
    monkeypatch.setattr(platform, 'system', lambda: 'LINUX')
    sct = mss.mss()
    assert isinstance(sct, MSSBase)

    # macOS
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    assert isinstance(exc.value[1]['self'], MSSBase)

    # Windows
    monkeypatch.setattr(platform, 'system', lambda: 'wInDoWs')
    with pytest.raises(ValueError):
        # wintypes.py:19: ValueError: _type_ 'v' not supported
        mss.mss()


def test_python_call():
    # __import__('mss.__main__')
    pytest.skip('Dunno how to test mss/__main__.py.')


@pytest.mark.skipif(
    platform.system().lower() != 'linux',
    reason='Specific to GNU/Linux.')
def test_gnu_linux(monkeypatch):
    text = str if sys.version[0] > '2' else unicode

    # Bad `display` type
    mss.mss(display=text(':0'))

    # TODO: SEGFAULT
    #with pytest.raises(ScreenShotError):
    #    mss.mss(display=text('0'))

    # No `DISPLAY` in envars
    monkeypatch.delenv('DISPLAY')
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()

    # No `X11` library
    x11 = ctypes.util.find_library('X11')
    monkeypatch.setattr(ctypes.util, 'find_library', lambda x: None)
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()

    def find_lib(lib):
        """
        Returns None to emulate no Xrandr library.
        Returns the previous found X11 library else.

        It is a naive approach, but works for now.
        """

        if lib == 'Xrandr':
            return None
        return x11

    # No `Xrandr` library
    monkeypatch.setattr(ctypes.util, 'find_library', find_lib)
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()

    # Bad display data
    import mss.linux
    monkeypatch.setattr(mss.linux, 'Display', lambda: None)
    mss.mss()


@pytest.mark.skipif(
    platform.system().lower() != 'darwin',
    reason='Specific to macOS.')
def test_macos(monkeypatch):
    # No `CoreGraphics` library
    monkeypatch.setattr(ctypes.util, 'find_library', lambda x: None)
    with pytest.raises(ScreenShotError):
        mss.mss()
    monkeypatch.undo()

    with mss.mss() as sct:
        # Test monitor's rotation
        original = sct.monitors[1]
        monkeypatch.setattr(sct.core, 'CGDisplayRotation',
                            lambda x: -90.0)
        sct._monitors = []
        modified = sct.monitors[1]
        assert original['width'] == modified['height']
        assert original['height'] == modified['width']
        monkeypatch.undo()

        # Test bad data retreival
        monkeypatch.setattr(sct.core, 'CGWindowListCreateImage',
                            lambda *args: None)
        with pytest.raises(ScreenShotError):
            sct.grab(sct.monitors[1])
        monkeypatch.undo()
