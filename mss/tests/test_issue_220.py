"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import pytest

import mss

tkinter = pytest.importorskip("tkinter")
root = tkinter.Tk()


def take_screenshot():
    region = {"top": 370, "left": 1090, "width": 80, "height": 390}
    with mss.mss() as sct:
        sct.grab(region)


def create_top_level_win():
    top_level_win = tkinter.Toplevel(root)

    take_screenshot_btn = tkinter.Button(top_level_win, text="Take screenshot", command=take_screenshot)
    take_screenshot_btn.pack()

    take_screenshot_btn.invoke()
    root.update_idletasks()
    root.update()

    top_level_win.destroy()
    root.update_idletasks()
    root.update()


def test_regression(capsys):
    btn = tkinter.Button(root, text="Open TopLevel", command=create_top_level_win)
    btn.pack()

    # First screenshot: it works
    btn.invoke()

    # Second screenshot: it should work too
    btn.invoke()

    # Check there were no exceptions
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err
