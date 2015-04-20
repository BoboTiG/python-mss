#!/usr/bin/env python
# coding: utf-8
''' A simple screen shot script.
    Use of python-mss: https://github.com/BoboTiG/python-mss/
    pip install --upgrade mss
'''

from platform import system
from mss import mss

if __name__ == '__main__':
    screnshotter = mss()
    for filename in screnshotter.save(output='monitor-%d.png', screen=1):
        print('File: "{0}" created.'.format(filename))
