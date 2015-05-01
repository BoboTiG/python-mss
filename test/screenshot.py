#!/usr/bin/env python
# coding: utf-8
''' A simple screenshot script using the MSS module.
    Use of python-mss: https://github.com/BoboTiG/python-mss/

    pip install --upgrade mss
'''

from __future__ import print_function

from mss import mss


screenshotter = mss()
for filename in screenshotter.save(output='monitor-%d.png', screen=1):
    print('File: "{0}" created.'.format(filename))
