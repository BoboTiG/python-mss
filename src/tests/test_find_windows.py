"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from mss import mss


def test_get_windows() -> None:
    with mss() as sct:
        assert sct.windows


def test_find_windows_by_name() -> None:
    with mss() as sct:
        source_window = sct.windows[0]
        target_window = sct.find_windows(name=source_window["name"])[0]
        assert source_window["name"] == target_window["name"]
        assert source_window["process"] == target_window["process"]
        assert source_window["bounds"]["top"] == target_window["bounds"]["top"]
        assert source_window["bounds"]["left"] == target_window["bounds"]["left"]
        assert source_window["bounds"]["width"] == target_window["bounds"]["width"]
        assert source_window["bounds"]["height"] == target_window["bounds"]["height"]


def test_find_windows_by_process() -> None:
    with mss() as sct:
        source_window = sct.windows[0]
        target_window = sct.find_windows(process=source_window["process"])[0]
        assert source_window["name"] == target_window["name"]
        assert source_window["process"] == target_window["process"]
        assert source_window["bounds"]["top"] == target_window["bounds"]["top"]
        assert source_window["bounds"]["left"] == target_window["bounds"]["left"]
        assert source_window["bounds"]["width"] == target_window["bounds"]["width"]
        assert source_window["bounds"]["height"] == target_window["bounds"]["height"]
