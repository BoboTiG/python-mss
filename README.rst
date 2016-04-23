************************************************************************************
An ultra fast cross-platform multiple screenshots module in pure python using ctypes
************************************************************************************

Very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file, Python 2.6/3.5 compatible & PEP8 compliant.
It could be easily embedded into games and other softwares which require fast and plateforme optimized methods to grab screenshots.

MSS stands for Multiple ScreenShots.

It's under zlib licence.


API change
==========

**Warning**: from the version 2.0.0 for specific system import, now you do as::

    # MacOS X
    from mss.darwin import MSS

    # GNU/Linux
    from mss.linux import MSS

    # Microsoft Windows
    from mss.windows import MSS

The second change is the split into several files. Each OS implementation is into a `platform.system()`.py. For GNU/Linux, you will find the `MSS` class into the file "mss/linux.py".

This make life easier for contributors and reviewers.


Installation
============

You can install it with pip::

    pip install --upgrade mss

Support
-------


=========  =========  ========  =======
Python     GNU/linux   MacOS X  Windows
=========  =========  ========  =======
**3.5.1**  **True**   **True**  **True**
3.4.3      True       True      True
3.3.6      True       True      True
3.2.6      True       True      True
3.1.5      True       True      True
3.0.1      True       True      True
**2.7.11** **True**   **True**  **True**
2.6.9      True       True      True
=========  =========  ========  =======

Feel free to try MSS on a system we had not tested, and let report us by creating an issue_.

.. _issue: https://github.com/BoboTiG/python-mss/issues


Testing
=======

You can try the MSS module directly from the console::

    python tests.py


Instance the good class
=======================

So MSS can be used as simply as::

    from mss import mss
    with mss() as screenshotter:
        # ...

Or import the good one::

    from mss.linux import MSS
    with MSS() as screenshotter:
        # ...


save(output, screen, callback)
------------------------------

For each monitor, grab a screenshot and save it to a file.

Parameters::

    output (str)
        The output filename.
        %d, if present, will be replaced by the monitor number.
    screen (int)
        -1: grab one screenshot of all monitors
         0: grab one screenshot by monitor
         N: grab the screenshot of the monitor N
    callback (def)
        In case where output already exists, call the defined callback
        function with output as parameter.
        If it returns True, then continue.
        Else ignores the monitor and switches to ne next.

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
