"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import pytest

import mss

tkinter = pytest.importorskip("tkinter")


@pytest.fixture
def root() -> tkinter.Tk:
    try:
        master = tkinter.Tk()
    except RuntimeError:
        pytest.skip(reason="tk.h version (8.5) doesn't match libtk.a version (8.6)")

    try:
        yield master
    finally:
        master.destroy()


def take_screenshot():
    region = {"top": 370, "left": 1090, "width": 80, "height": 390}
    with mss.mss() as sct:
        sct.grab(region)


def create_top_level_win(master: tkinter.Tk):
    top_level_win = tkinter.Toplevel(master)

    take_screenshot_btn = tkinter.Button(top_level_win, text="Take screenshot", command=take_screenshot)
    take_screenshot_btn.pack()

    take_screenshot_btn.invoke()
    master.update_idletasks()
    master.update()

    top_level_win.destroy()
    master.update_idletasks()
    master.update()


def test_regression(root: tkinter.Tk, capsys):
    btn = tkinter.Button(root, text="Open TopLevel", command=lambda: create_top_level_win(root))
    btn.pack()

    # First screenshot: it works
    btn.invoke()

    # Second screenshot: it should work too
    btn.invoke()

    # Check there were no exceptions
    captured = capsys.readouterr()
    assert not captured.out
    assert not captured.err
