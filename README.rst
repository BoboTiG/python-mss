**********************************************************************
A cross-platform multi-screen shot module in pure python using ctypes
**********************************************************************

Very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to an optimised PNG file, Python 2.7/3.3 compatible.

So, while you can `pip install mss`, you may just drop it in your project and forget about it.

MSS stands for Multi-Screen Shot.

It's under zlib licence.


Testing
=======

You can try the MSS module directly from the console::

    python mss.py [--debug]

Passing the `--debug` argument will make it more verbose.


Instance the good class
========================

You can determine automatically which class to use::

    from platform import system
    import mss

    systems = {
        'Darwin' : mss.MSSMac,
        'Linux'  : mss.MSSLinux,
        'Windows': mss.MSSWindows
    }
    try:
        MSS = systems[system()]
    except KeyError:
        err = 'System "{0}" not implemented.'.format(system())
        raise NotImplementedError(err)

Or simply import the good one::

    from mss import MSSLinux as MSS


init(debug=False)
-----------------

When initalising an instance of MSS, you can enable debug output::

    mss = MSS(debug=True)


save(output='mss', oneshot=False)
-----------------------------------------------------

For each monitor, grab a screen shot and save it to a file.

Parameters::

    output - string - the output filename without extension
    oneshot - boolean - grab only one screen shot of all monitors

This is a generator which returns created files::

    'output-1.png',
    'output-2.png',
    ...,
    'output-NN.png'
    or
    'output-full.png'


Example
========

Then, it is quite simple::

    try:
        mss = MSS()

        # One screen shot per monitor
        for filename in mss.save():
            print('File "{0}" created.'.format(filename))

        # A shot to grab them all :)
        for filename in mss.save(oneshot=True):
            print('File "{0}" created.'.format(filename))
    except (OSError, ValueError) as ex:
        print(ex)
        raise


Bonus
======

Just for fun ...
Show us your screen shot with all monitors in one file, we will update the gallery.

Link to the galley: https://tiger-222.fr/tout/python-mss/galerie/
