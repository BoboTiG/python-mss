"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Usage example with a specific display.
"""
import mss

with mss.mss(display=":0.0") as sct:
    for filename in sct.save():
        print(filename)
