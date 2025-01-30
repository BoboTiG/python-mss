"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from mss import mss

def test_get_windows() -> None:
    with mss() as sct:
        assert sct.windows
