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
    :lines: 8-


Part of the screen
------------------

You can capture only a part of the screen:

.. literalinclude:: examples/part_of_screen.py
    :lines: 8-

.. versionadded:: 3.0.0


Part of the screen of the 2nd monitor
-------------------------------------

This is an example of capturing some part of the screen of the monitor 2:

.. literalinclude:: examples/part_of_screen_monitor_2.py
    :lines: 8-

.. versionadded:: 3.0.0


Use PIL bbox style and percent values
-------------------------------------

You can use the same value as you would do with ``PIL.ImageGrab(bbox=tuple(...))``.
This is an example that uses it, but also using percentage values:

.. literalinclude:: examples/from_pil_tuple.py
    :lines: 8-

.. versionadded:: 3.1.0

PNG Compression
---------------

You can tweak the PNG compression level (see :py:func:`zlib.compress()` for details)::

    sct.compression_level = 2

.. versionadded:: 3.2.0

Get PNG bytes, no file output
-----------------------------

You can get the bytes of the PNG image:
::

    with mss.mss() as sct:
        # The monitor or screen part to capture
        monitor = sct.monitors[1]  # or a region

        # Grab the data
        sct_img = sct.grab(monitor)

        # Generate the PNG
        png = mss.tools.to_png(sct_img.rgb, sct_img.size)

Advanced
========

You can handle data using a custom class:

.. literalinclude:: examples/custom_cls_image.py
    :lines: 8-

.. versionadded:: 3.1.0

PIL
===

You can use the Python Image Library (aka Pillow) to do whatever you want with raw pixels.
This is an example using `frombytes() <http://pillow.readthedocs.io/en/latest/reference/Image.html#PIL.Image.frombytes>`_:

.. literalinclude:: examples/pil.py
    :lines: 8-

.. versionadded:: 3.0.0

Playing with pixels
-------------------

This is an example using `putdata() <https://github.com/python-pillow/Pillow/blob/b9b5d39f2b32cec75b9cf96b882acb7a77a4ed4b/PIL/Image.py#L1523>`_:

.. literalinclude:: examples/pil_pixels.py
    :lines: 8-

.. versionadded:: 3.0.0

OpenCV/Numpy
============

See how fast you can record the screen.
You can easily view a HD movie with VLC and see it too in the OpenCV window.
And with __no__ lag please.

.. literalinclude:: examples/opencv_numpy.py
    :lines: 8-

.. versionadded:: 3.0.0

FPS
===

Benchmark
---------

Simple naive benchmark to compare with `Reading game frames in Python with OpenCV - Python Plays GTA V <https://pythonprogramming.net/game-frames-open-cv-python-plays-gta-v/>`_:

.. literalinclude:: examples/fps.py
    :lines: 9-

.. versionadded:: 3.0.0

Multiprocessing
---------------

Performances can be improved by delegating the PNG file creation to a specific worker.
This is a simple example using the :py:mod:`multiprocessing` inspired by the `TensorFlow Object Detection Introduction <https://github.com/pythonlessons/TensorFlow-object-detection-tutorial>`_ project:

.. literalinclude:: examples/fps_multiprocessing.py
    :lines: 9-

.. versionadded:: 5.0.0


BGRA to RGB
===========

Different possibilities to convert raw BGRA values to RGB::

    def mss_rgb(im):
        """ Better than Numpy versions, but slower than Pillow. """
        return im.rgb


    def numpy_flip(im):
        """ Most efficient Numpy version as of now. """
        frame = numpy.array(im, dtype=numpy.uint8)
        return numpy.flip(frame[:, :, :3], 2).tobytes()


    def numpy_slice(im):
        """ Slow Numpy version. """
        return numpy.array(im, dtype=numpy.uint8)[..., [2, 1, 0]].tobytes()


    def pil_frombytes(im):
        """ Efficient Pillow version. """
        return Image.frombytes('RGB', im.size, im.bgra, 'raw', 'BGRX').tobytes()


    with mss.mss() as sct:
        im = sct.grab(sct.monitors[1])
        rgb = pil_frombytes(im)
        ...

.. versionadded:: 3.2.0
