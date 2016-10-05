========
Examples
========

GNU/Linux
---------

Usage example with a specific display::

    from mss.linux import MSS


    display = ':0.0'
    print('Screenshot of display "{0}"'.format(display))
    output = 'monitor{0}-%d.png'.format(display)

    with MSS(display=display) as screenshotter:
        for filename in screenshotter.save(output=output):
            print(filename)


Using PIL
---------

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
