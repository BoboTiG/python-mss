========
Examples
========

Basics
======

One screen shot per monitor
---------------------------
::

    for filename in sct.save():
        print(filename)

Screen shot of the monitor 1
----------------------------
::

    filename = sct.shot()
    print(filename)

A screen shot to grab them all
------------------------------
::

    filename = sct.shot(mon=-1, output='fullscreen.png')
    print(filename)

Callback
--------

Screen shot of the monitor 1 with a callback:

.. literalinclude:: examples/callback.py
    :lines: 9-


Part of the screen
------------------

You can capture only a part of the screen:

.. literalinclude:: examples/part_of_screen.py
    :lines: 9-

.. versionadded:: 3.0.0

Use PIL bbox style and percent values
-------------------------------------

You can use the same value as you would do with ``PIL.ImageGrab(bbox=tuple(...))``.
This is an example that uses it, but also using percentage values:

.. literalinclude:: examples/from_pil_tuple.py
    :lines: 9-

.. versionadded:: 3.1.0

PNG Compression
---------------

You can tweak the PNG compression level (see :py:func:`zlib.compress()` for details)::

    sct.compression_level = 2

.. versionadded:: 3.2.0

Advanced
========

You can handle data using a custom class:

.. literalinclude:: examples/custom_cls_image.py
    :lines: 9-

.. versionadded:: 3.1.0

PIL
===

You can use the Python Image Library (aka Pillow) to do whatever you want with raw pixels.
This is an example using `frombytes() <http://pillow.readthedocs.io/en/latest/reference/Image.html#PIL.Image.frombytes>`_:

.. literalinclude:: examples/pil.py
    :lines: 9-

.. versionadded:: 3.0.0

Playing with pixels
-------------------

This is an example using `putdata() <https://github.com/python-pillow/Pillow/blob/b9b5d39f2b32cec75b9cf96b882acb7a77a4ed4b/PIL/Image.py#L1523>`_:

.. literalinclude:: examples/pil_pixels.py
    :lines: 9-

.. versionadded:: 3.0.0

OpenCV/Numpy
============

See how fast you can record the screen.
You can easily view a HD movie with VLC and see it too in the OpenCV window.
And with __no__ lag please.

.. literalinclude:: examples/opencv_numpy.py
    :lines: 9-

.. versionadded:: 3.0.0

FPS
===

Benchmark
---------

Simple naive benchmark to compare with `Reading game frames in Python with OpenCV - Python Plays GTA V <https://pythonprogramming.net/game-frames-open-cv-python-plays-gta-v/>`_:

.. literalinclude:: examples/fps.py
    :lines: 12-

.. versionadded:: 3.0.0
