"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Screenshot of the monitor 1, with callback.
"""

from pathlib import Path

import mss


def on_exists(fname: str) -> None:
    """Callback example when we try to overwrite an existing screenshot."""
    file = Path(fname)
    if file.is_file():
        newfile = file.with_name(f"{file.name}.old")
        print(f"{fname} → {newfile}")
        file.rename(newfile)


with mss.mss() as sct:
    filename = sct.shot(output="mon-{mon}.png", callback=on_exists)
    print(filename)
