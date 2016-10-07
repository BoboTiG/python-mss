========
Examples
========

Basics
======

One screenshot per monitor::

    for filename in screenshotter.save():
        print(filename)


Screenshot of the monitor 1::

    next(screenshotter.save(mon=1))


A screenshot to grab them all::

    next(screenshotter.save(mon=-1, output='fullscreen.png'))


Callback
--------

Screenshot of the monitor 1 with callback::

    from os import rename
    from os.path import isfile


    def on_exists(fname):
        ''' Callback example when we try to overwrite an existing screenshot. '''

        if isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            rename(fname, newfile)
        return True

    next(screenshotter.save(mon=1, callback=on_exists))


Into the Python's console
-------------------------

::

    >>> from mss import mss
    >>> sct = mss(display=':0')

    # Retrieve monitors informations
    >>> displays = sct.enum_display_monitors()
    >>> displays
    [{'width': 1920, 'top': 0, 'height': 1080, 'left': 0}, {'width': 1920, 'top': 0, 'height': 1080, 'left': 0}]
    # You can access monitors list via `monitors`:
    >>> displays is sct.monitors
    True

    # Retrieve pixels from the first monitor
    >>> pixels = sct.get_pixels(displays[1])
    >>> type(pixels)
    <class 'bytes'>
    # You can access pixels data via `image`:
    >>> pixels is sct.image
    True

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


GNU/Linux
=========

On GNU/Linux, you can specify which display to use (useful for distant screenshots via SSH)::

    from mss.linux import MSS


    display = ':0.0'
    print('Screenshot of display "{0}"'.format(display))
    output = 'monitor{0}-%d.png'.format(display)

    with MSS(display=display) as screenshotter:
        for filename in screenshotter.save(output=output):
            print(filename)


Using PIL
=========

You can use the Python Image Library (aka Pillow) to do whatever you want with raw pixels.
This is an example using `frombytes() <http://pillow.readthedocs.io/en/latest/reference/Image.html#PIL.Image.frombytes>`_::

    from mss import mss
    from PIL import Image


    with mss() as screenshotter:
        # We retrieve monitors informations:
        monitors = screenshotter.enum_display_monitors()

        # Get rid of the first, as it represents the "All in One" monitor:
        for num, monitor in enumerate(monitors[1:], 1):
            # Get raw pixels from the screen.
            # This method will store screen size into `width` and `height`
            # and raw pixels into `image`.
            screenshotter.get_pixels(monitor)

            # Create an Image:
            img = Image.frombytes('RGB',
                                  (screenshotter.width, screenshotter.height),
                                  screenshotter.image)

            # And save it!
            img.save('monitor-{0}.jpg'.format(num))
