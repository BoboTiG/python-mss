**********************************************************************
A cross-platform multi-screen shot module in pure python using ctypes
**********************************************************************

Very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to an optimised PNG file, Python 2.7/3.4 compatible & PEP8 compliant.

So, while you can `pip install --upgrade mss`, you may just drop it in your project and forget about it.

MSS stands for Multi-Screen Shot.

It's under zlib licence.


Testing
=======

You can try the MSS module directly from the console::

    python2 mss.py [--debug]
    python3 -X faulthandler mss.py

Passing the `--debug` argument will make it more verbose.


Instance the good class
=======================

You can determine automatically which class to use::

    from platform import system
    import mss

    systems = {
        'Darwin': mss.MSSMac,
        'Linux': mss.MSSLinux,
        'Windows': mss.MSSWindows
        }
    mss_class = systems[system()]

Or simply import the good one::

    from mss import MSSLinux as mss_class


init(debug)
-----------

When initialising an instance of MSS, you can enable debug output::

    mss = mss_class(debug=True)


save(output, screen, callback)
------------------------------

For each monitor, grab a screen shot and save it to a file.

Parameters::

    output - string - the output filename. It can contain '%d' which
                      will be replaced by the monitor number.
    screen - integer - grab one screen shot of all monitors (screen=-1)
                       grab one screen shot by monitor (screen=0)
                       grab the screen shot of the monitor N (screen=N)
    callback - function - in case where output already exists, call
                          the defined callback function with output
                          as parameter. If it returns True, then
                          continue; else ignores the monitor and
                          switches to ne next.

This is a generator which returns created files.


Examples
========

Then, it is quite simple::

    mss = mss_class()

    try:
        # One screen shot per monitor
        for filename in mss.save():
            print('File: "{}" created.'.format(filename))

        # Screen shot of the monitor 1
        for filename in mss.save(output='monitor-%d.png', screen=1):
            print('File: "{}" created.'.format(filename))

        # A shot to grab them all :)
        for filename in mss.save(output='full-screenshot.png', screen=-1):
            print('File: "{}" created.'.format(filename))

        # Example with a callback
        def on_exists(fname):
            ''' Callback example when we try to overwrite an existing screen shot. '''

            from os import rename
            newfile = fname + '.old'
            print('Renaming "{}" to "{}"'.format(fname, newfile))
            rename(fname, newfile)
            return True

        # Screen shot of the monitor 1, with callback
        for fname in mss.save(output='mon-%d.png', screen=1, callback=on_exists):
            print('File: "{}" created.'.format(fname))
    except ScreenshotError as ex:
        print(ex)
