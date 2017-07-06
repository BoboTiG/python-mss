========
Examples
========

Basics
======

One screenshot per monitor::

    for filename in sct.save():
        print(filename)

Screenshot of the monitor 1::

    filename = sct.shot()
    print(filename)

A screenshot to grab them all::

    filename = sct.shot(mon=-1, output='fullscreen.png')
    print(filename)

Callback
--------

Screenshot of the monitor 1 with a callback:

.. literalinclude:: examples/callback.py
    :lines: 9-

GNU/Linux
---------

On GNU/Linux, you can specify which display to use (useful for distant screenshots via SSH):

.. literalinclude:: examples/linux_display_keyword.py
    :lines: 9-

Part of the screen
------------------

You can capture only a part of the screen:

.. literalinclude:: examples/part_of_screen.py
    :lines: 9-

PIL
===

You can use the Python Image Library (aka Pillow) to do whatever you want with raw pixels.
This is an example using `frombytes() <http://pillow.readthedocs.io/en/latest/reference/Image.html#PIL.Image.frombytes>`_:

.. literalinclude:: examples/pil.py
    :lines: 9-

Playing with pixels
-------------------

This is an example using `putdata() <https://github.com/python-pillow/Pillow/blob/b9b5d39f2b32cec75b9cf96b882acb7a77a4ed4b/PIL/Image.py#L1523>`_:

.. literalinclude:: examples/pil_pixels.py
    :lines: 9-

OpenCV/Numpy
============

See how fast you can record the screen.
You can easily view a HD movie with VLC and see it too in the OpenCV window.
And with __no__ lag please.

.. literalinclude:: examples/opencv_numpy.py
    :lines: 9-

FPS
===

Benchmark
---------

Simple naive benchmark to compare with `Reading game frames in Python with OpenCV - Python Plays GTA V <https://pythonprogramming.net/game-frames-open-cv-python-plays-gta-v/>`_:

.. literalinclude:: examples/fps.py
    :lines: 12-
