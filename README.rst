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


init(debug=False)
-----------------

When initialising an instance of MSS, you can enable debug output::

    mss = mss_class(debug=True)


save(output='screenshot', screen=-1, callback=lambda *x: True)
--------------------------------------------------------------

For each monitor, grab a screen shot and save it to a file.

Parameters::

    output - string - the output filename without extension
    screen - integer - grab one screen shot of all monitors (screen=-1)
                       grab one screen shot by monitor (screen=0)
                       grab the screen shot of the monitor N (screen=N)
    callback - function - in case where output already exists, call
                          the defined callback function with output
                          as parameter. If it returns True, then
                          continue; else ignores the monitor and
                          switches to ne next.

This is a generator which returns created files::

    'screenshot-1.png',
    'screenshot-2.png',
    ...,
    'screenshot-N.png'
    or
    'screenshot-full.png'


Examples
========

Then, it is quite simple::

    mss = mss_class()

    # One screen shot per monitor
    for filename in mss.save():
        print('File: "{}" created.'.format(filename))

    # Screen shot of the monitor 1
    for filename in mss.save(output='monitor-1', screen=1):
        print('File: "{}" created.'.format(filename))

    # A shot to grab them all :)
    for filename in mss.save(screen=-1):
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
    for filename in mss.save(output='monitor-1', screen=1, callback=on_exists):
        print('File: "{}" created.'.format(filename))


Bonus
=====

Just for fun ...
Show us your screen shot with all monitors in one file, we will update the gallery.

Link to the galley: https://tiger-222.fr/tout/python-mss/galerie/
