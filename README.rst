**********************************************************************
A cross-platform multi-screen shot module in pure python using ctypes
**********************************************************************

Very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file, Python 2.6/3.5 compatible & PEP8 compliant.
It could be easily embedded into games and other softwares which require fast and plateforme optimized methods to grab screenshots.

MSS stands for Multiple ScreenShots.

It's under zlib licence.


Installation
============

You can install it with pip::

    pip install --upgrade mss

Or you may just drop it in your project and forget about it.

Support
-------

=========  =========  ========  =======
Python     GNU/linux  Mac OS X  Windows
=========  =========  ========  =======
3.5.0a3    True       True      True
**3.4.3**  **True**   **True**  **True**
3.3.6      True       True      True
3.2.6      True       True      True
3.1.5      True       True      True
3.0.1      True       True      True
**2.7.9**  **True**   **True**  **True**
2.6.9      True       True      True
=========  =========  ========  =======

Feel free to try MSS on a system we had not tested, and let report us by creating an issue_.

.. _issue: https://github.com/BoboTiG/python-mss/issues


Testing
=======

You can try the MSS module directly from the console::

    python mss.py


Instance the good class
=======================

So MSS can be used as simply as::

    from mss import mss
    screenshotter = mss()

Or import the good one::

    from mss import MSSLinux as mss
    screenshotter = mss()


save(output, screen, callback)
------------------------------

For each monitor, grab a screenshot and save it to a file.

Parameters::

    output - string - the output filename. It can contain '%d' which
                      will be replaced by the monitor number.
    screen - integer - grab one screenshot of all monitors (screen=-1)
                       grab one screenshot by monitor (screen=0)
                       grab the screenshot of the monitor N (screen=N)
    callback - function - in case where output already exists, call
                          the defined callback function with output
                          as parameter. If it returns True, then
                          continue; else ignores the monitor and
                          switches to ne next.

This is a generator which returns created files.


Examples
========

One screenshot per monitor::

    for filename in screenshotter.save():
        print(filename)

Screenshot of the monitor 1::

    for filename in screenshotter.save(screen=1):
        print(filename)

Screenshot of the monitor 1, with callback::

    def on_exists(fname):
        ''' Callback example when we try to overwrite an existing
            screenshot.
        '''
        from os import rename
        from os.path import isfile
        if isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            rename(fname, newfile)
        return True

    for filename in screenshotter.save(screen=1, callback=on_exists):
        print(filename)

A screenshot to grab them all::

    for filename in screenshotter.save(output='fullscreen-shot.png', screen=-1):
        print(filename)
