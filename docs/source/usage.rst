=====
Usage
=====

Instance the good class
-----------------------

So MSS can be used as simply as::

    from mss import mss

    with mss() as screenshotter:
        # ...


Or import the good one (choose one)::

    # MacOS X
    from mss.darwin import MSS

    # GNU/Linux
    from mss.linux import MSS

    # Microsoft Windows
    from mss.windows import MSS

    with MSS() as screenshotter:
        # ...


Of course, you can use it the old way::

    from mss import mss
    # or from mss.linux import MSS as mss

    screenshotter = mss()


Examples
--------

One screenshot per monitor::

    for filename in screenshotter.save():
        print(filename)

Screenshot of the monitor 1::

    print(next(screenshotter.save(mon=1)))

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

    print(next(screenshotter.save(mon=1, callback=on_exists)))

A screenshot to grab them all::

    print(next(screenshotter.save(mon=-1, output='fullscreen.png')))


Into the Python's console
-------------------------

.. code:: python

    >>> from mss import mss
    >>> sct = mss(display=b':0')

    # Retrieve monitors informations
    >>> displays = sct.enum_display_monitors()
    >>> displays
    [{'width': 1920, 'top': 0, 'height': 1080, 'left': 0}, {'width': 1920, 'top': 0, 'height': 1080, 'left': 0}]
    # You can access monitors list via `monitors`:
    >>> sct.monitors
    [{'width': 1920, 'top': 0, 'height': 1080, 'left': 0}, {'width': 1920, 'top': 0, 'height': 1080, 'left': 0}]

    # Retrieve pixels from the first monitor
    >>> pixels = sct.get_pixels(displays[1])
    >>> pixels
    <ctypes.c_char_Array_6220800 object at 0x7fe82e9007a0>
    # You can access pixels data via `image`:
    >>> sct.image
    <ctypes.c_char_Array_6220800 object at 0x7fe82e9007a0>

    # Save pixels to a PNG file: option 1
    >>> files = sct.save(mon=1)
    >>> next(files)
    'monitor-1.png'
    >>> next(files)
    Traceback (most recent call last):
    File "<stdin>", line 1, in <module>
    StopIteration

    # Save pixels to a PNG file: option 2
    >>> mon = displays[1]
    >>> sct.to_png(data=pixels, width=mon['width'], height=mon['height'], output='monitor-1.png')
