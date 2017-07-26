# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Usage example with a specific display.
"""

from mss.linux import MSS


with MSS(display=':0.0') as sct:
    for filename in sct.save():
        print(filename)
