#!/usr/bin/env python
# coding: utf-8
''' A simple screen shot script.
    Use of python-mss: https://github.com/BoboTiG/python-mss/
    pip install --upgrade mss
'''

from platform import system
import mss

systems = {
    'Darwin': mss.MSSMac,
    'Linux': mss.MSSLinux,
    'Windows': mss.MSSWindows
}
mss_class = systems[system()]

if __name__ == '__main__':
    mss = mss_class()
    for filename in mss.save(output='monitor-%d.png', screen=1):
        print('File: "{0}" created.'.format(filename))
