# coding: utf-8

import ctypes.util
import platform
import sys

import pytest

import mss
from mss.base import MSSBase
from mss.exception import ScreenShotError


if platform.system().lower() != 'linux':
    pytestmark = pytest.mark.skip


TEXT = str if sys.version[0] > '2' else unicode
PY3 = sys.version[0] > '2'


def test_factory_systems(monkeypatch):
    """
    Here, we are testing all systems.

    Too hard to maintain the test for all platforms,
    so est only on GNU/Linux.
    """

    # GNU/Linux
    monkeypatch.setattr(platform, 'system', lambda: 'LINUX')
    sct = mss.mss()
    assert isinstance(sct, MSSBase)

    # macOS
    monkeypatch.setattr(platform, 'system', lambda: 'Darwin')
    with pytest.raises(ScreenShotError) as exc:
        mss.mss()
    if not PY3:
        error = exc.value[1]['self']
    else:
        error = exc.value.args[1]['self']
    assert isinstance(error, MSSBase)

    # Windows
    monkeypatch.setattr(platform, 'system', lambda: 'wInDoWs')
    with pytest.raises(ValueError):
        # wintypes.py:19: ValueError: _type_ 'v' not supported
        mss.mss()


def test_implementation(monkeypatch):
    import mss

    # Bad `display` type
    mss.mss(display=TEXT(':0'))

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
    with pytest.raises(TypeError):
        mss.mss()
