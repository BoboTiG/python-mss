# coding: utf-8

import ctypes.util
import platform

import mss
from mss.exception import ScreenShotError

import pytest


if platform.system().lower() != "windows":
    pytestmark = pytest.mark.skip


def test_implementation(monkeypatch):
    # Test bad data retrieval
    with mss.mss() as sct:
        monkeypatch.setattr(ctypes.windll.gdi32, "GetDIBits", lambda *args: 0)
        with pytest.raises(ScreenShotError):
            sct.shot()
        monkeypatch.undo()
