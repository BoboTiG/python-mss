"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Screenshot of the monitor 1, with callback.
"""
import os
import os.path

import mss


def on_exists(fname: str) -> None:
    """
    Callback example when we try to overwrite an existing screenshot.
    """

    if os.path.isfile(fname):
        newfile = f"{fname}.old"
        print(f"{fname} -> {newfile}")
        os.rename(fname, newfile)


with mss.mss() as sct:
    filename = sct.shot(output="mon-{mon}.png", callback=on_exists)
    print(filename)
