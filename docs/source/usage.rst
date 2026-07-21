=====
Usage
=====

.. role:: python(code)
   :language: python
   :class: highlight

Import
======

MSS can be used simply as::

    from mss import MSS

    with MSS() as sct:
        # ...

For compatibility with existing code, :py:func:`mss.mss` is still available in
11.0, but deprecated::

    import mss

    with mss.mss() as sct:  # Deprecated in 10.2
        # ...

For compatibility with existing code, platform-specific class names are also
still available in 11.0, but are also deprecated::

    # GNU/Linux
    from mss.linux import MSS

    # macOS
    from mss.darwin import MSS

    # Microsoft Windows
    from mss.windows import MSS

Capturing Screenshots
=====================

If you simply need to capture one or more monitors to PNG files, the :ref:`examples` section has code ready for you to
copy and paste.

If instead you want to use the pixel data yourself, you can do so easily, with the :py:meth:`mss.MSS.grab` method.

You'll first need to decide whether you want to capture all the monitors, a single monitor, or a specific region of the
screen.

For capturing one or more monitors, the :py:class:`mss.MSS` object has a :py:attr:`mss.MSS.monitors` attribute that is a
list of all the monitors, starting from index 1, as well as the full virtual screen (all monitors combined) at index 0.
The primary monitor, the one that holds the taskbar or similar system UI, is available as
:py:attr:`mss.MSS.primary_monitor`.

For capturing a specific region, you can pass :py:meth:`mss.MSS.grab` a dictionary with the keys ``top``, ``left``,
``width``, and ``height``.  For instance, to capture a 100x100 pixel region starting at the top-left corner of the
screen, you could use :python:`{"top": 0, "left": 0, "width": 100, "height": 100}`.  You can also use a PIL-style box,
which is a 4-tuple of ``(left, top, right, bottom)``.

Once you've decided what you want to capture, you can call :py:meth:`mss.MSS.grab` with the appropriate monitor or
region.  This will return a :py:class:`mss.ScreenShot` object, which contains the pixel data and other information about
the screenshot.

For instance, you can capture the first monitor and get a :py:class:`mss.ScreenShot` object like this::

    with MSS() as sct:
        sct_img = sct.grab(sct.primary_monitor)

Ok, now you've got the :py:class:`mss.ScreenShot` object.  But what do
you do with it?

.. _accessing_pixel_data:

Accessing Pixel Data
====================

Once you have the :py:class:`mss.ScreenShot` object, you'll want to use the pixel data.  There are several ways,
depending on what you want to do with it.  This is a quick overview of the options, with more details in the linked
references.

If you want to examine individual pixels, you can get them from the :py:class:`mss.ScreenShot` object directly, using
any of several methods:

* :py:attr:`mss.ScreenShot.bgra`: (fastest) Direct access to the pixel data, as a :py:class:`memoryview` of
  ``BGRABGRA...`` bytes.
* :py:attr:`mss.ScreenShot.rgb`: A :py:class:`memoryview` of ``RGBRGB...`` bytes.
* :py:attr:`mss.ScreenShot.pixels`: A 2d array (list of lists) of ``(R, G, B)`` tuples.
* :py:meth:`mss.ScreenShot.pixel`: Access ``(R, G, B)`` tuples of a particular x, y coordinate.

Often, though, you'll export screenshot data to a different framework.  You can often do this by passing the
:py:attr:`mss.ScreenShot.bgra` data to the framework's appropriate function.  MSS also provides easy-to-use methods to
work with many popular frameworks:

* :py:meth:`mss.ScreenShot.to_pil`: Creates a :py:class:`PIL.Image.Image` for use with the popular Python Imaging
  Library, `Pillow <https://pillow.readthedocs.io/>`_.  This provides a wide range of image manipulation capabilities,
  including saving to many different formats.
* :py:meth:`mss.ScreenShot.to_numpy`: Creates a :py:class:`numpy.ndarray` for use with the high-speed NumPy scientific
  computing library.  This is compatible with most other Python frameworks that have image manipulation capabilities,
  such as `scikit-image <https://scikit-image.org/>`_ and `OpenCV <https://opencv.org/>`_.
* :py:meth:`mss.ScreenShot.to_torch`: Creates a :py:class:`torch.Tensor` for use with
  `PyTorch <https://pytorch.org/>`_, a popular deep learning framework.
* :py:meth:`mss.ScreenShot.to_tensorflow`: Creates a :py:class:`tf.Tensor` for use with
  `TensorFlow <https://www.tensorflow.org/>`_, another popular deep learning framework.

NumPy Array Interface Protocol
------------------------------

Many libraries support the `NumPy array interface protocol
<https://numpy.org/doc/stable/reference/arrays.interface.html>`_.  This allows them to accept a
:py:class:`mss.ScreenShot` object directly to these libraries, without needing to convert it to a NumPy array first.
Some examples include the following libraries:

* Many `SciPy <https://scipy.org/>`_ projects
* `CuPy <https://cupy.dev/>`_, a GPU-accelerated NumPy-like library
* `JAX <https://jax.dev/>`_, a high-performance machine learning library
* `Pandas <https://pandas.pydata.org/>`_, a popular data analysis library
* `scikit-learn <https://scikit-learn.org/>`_, a popular machine learning library
* `Matplotlib <https://matplotlib.org/>`_, a popular plotting library
* Some functions from `OpenCV <https://opencv.org/>`_, a popular computer vision library

When using the NumPy array interface protocol, the returned object is in HWC (height, width, channels) format, with the
channels in BGRA order, and with a data type of :py:attr:`numpy.uint8`.

Note that most libraries do not expect the alpha channel to be present, or expect an order other than the BGRA order
used in this automatic conversion.  You may prefer to use the :py:meth:`mss.ScreenShot.to_numpy` method instead, since
it can return the pixel data in most common layouts, orders, and data types.

Alpha Channel
-------------

The alpha channel is used for transparency in images.  However, it's also sometimes just used as a placeholder for an
unused channel.  In the case of screenshots, the alpha channel is often not used for transparency, and may be filled
with zeros.  If an image processing library interprets the alpha channel as transparency, this can make it think the
image is transparent.

For instance, if you use Matplotlib to display a screenshot, you might see nothing at all.  This happens if the OS has
filled the alpha channel with zeros (which is common on many platforms).

The methods described above, such as :py:meth:`mss.ScreenShot.to_numpy`, can convert the pixel data to BGR (or RGB)
format, removing the alpha channel entirely.

In other words, instead of ``plt.imshow(img)``, you can use ``plt.imshow(img.to_numpy(channels="RGB"))`` to display the
screenshot correctly.

In the future, MSS may provide an indicator of whether the alpha channel is meaningful or not, as well as whether it is
premultiplied or straight alpha.  For now, you should assume that the alpha channel is not meaningful, and either ignore
or remove it, unless you know that it's meaningful for your specific circumstances.

Memory Sharing
--------------

There's a subtlety to be aware of in the following conditions:

1. You are using any of the above methods (or properties, or the NumPy array interface protocol) to convert a
   :py:class:`mss.ScreenShot` object to another format, *and*
2. You use two different methods, or the same method twice, on the same :py:class:`mss.ScreenShot` object, *and*
3. You modify the pixel data of the returned object (e.g., a NumPy array or a PIL image).

When using any of the above methods, the returned object might (but does not always) share pixel memory with the
original :py:class:`mss.ScreenShot` object.  This means that if you modify the returned object's pixels, it may also
modify the pixels stored in the original :py:class:`mss.ScreenShot` object, or other objects that share the same memory.

For instance, if you use :py:meth:`mss.ScreenShot.to_numpy` to create a NumPy array, then use
:py:meth:`mss.ScreenShot.to_pil` to create a PIL image, both objects may share the same memory.  If you modify the
pixels of the NumPy array, it may also modify the pixels of the PIL image, and vice versa.

Pixel memory is never guaranteed to be shared; it depends on many specifics.  Whether memory is shared or not is an
implementation detail, and not part of the semantic versioning guarantees of MSS: it may change in future versions,
or even when a program is run in different environments.

If you want to ensure that memory is not shared, you can make a copy of the returned object.  For instance, if you
want to ensure that a NumPy array does not share memory with the original :py:class:`mss.ScreenShot` object, you can
use the :py:meth:`numpy.ndarray.copy` method to create a copy of the array.

Intensive Use
=============

If you plan to integrate MSS inside your own module or software, pay attention to using it wisely.

This is a bad usage::

    for _ in range(100):
        with MSS() as sct:
            sct.shot()

This is a much better usage, memory efficient::

    with MSS() as sct:
        for _ in range(100):
            sct.shot()

Also, it is a good thing to save the MSS instance inside an attribute of your class and calling it when needed.

Direct Screenshot Buffers
=========================

On supported platforms, MSS can expose screenshot data directly from operating system buffers instead of copying it into
a separate Python-owned buffer. This reduces memory copying and can improve performance when processing screenshots with
libraries that support the Python buffer protocol, such as NumPy and OpenCV.

This optimization is enabled automatically and does not require any changes to application code.

Requirements:

- Python 3.12 or later
- GNU/Linux

Support for additional operating systems is planned.

Multithreading
==============

MSS is thread-safe and can be used from multiple threads.

**Sharing one MSS object**: You can use the same MSS object from multiple threads.  Calls to
:py:meth:`mss.MSS.grab` (and other capture methods) are serialized automatically, meaning only one thread
will capture at a time.  This may be relaxed in a future version if it can be done safely.

**Using separate MSS objects**: You can also create different MSS objects in different threads.  Whether these run
concurrently or are serialized by the OS depends on the platform.

Custom :py:class:`mss.screenshot.ScreenShot` classes (see :ref:`custom_cls_image`) must **not** call
:py:meth:`mss.MSS.grab` in their constructor.

.. danger::
    These guarantees do not apply to the obsolete Xlib backend.  That backend
    is only used if you specifically request it, so you won't be caught
    off-guard.

.. versionadded:: 10.2.0
    Prior to this version, on some operating systems, the MSS object could only be used on the thread on which it was
    created.

.. _backends:

Backends
========

Some platforms have multiple ways to take screenshots.  In MSS, these are known as *backends*.  The :py:class:`mss.MSS`
constructor will normally autodetect which one is appropriate for your situation, but you can override this if you want.
For instance, you may know that your specific situation requires a particular backend.

If you want to choose a particular backend, you can pass the ``backend`` keyword to :py:class:`mss.MSS`::

    with MSS(backend="xgetimage") as sct:
        ...

GNU/Linux has multiple backend implementations. Windows also exposes the named ``gdi`` backend, which is currently the same as ``default``. The GNU/Linux backends are described in their own section below.


GNU/Linux
---------

Display
^^^^^^^

On GNU/Linux, the default display is taken from the :envvar:`DISPLAY` environment variable.  You can instead specify which display to use (useful for distant screenshots via SSH) using the ``display`` keyword:

.. literalinclude:: examples/linux_display_keyword.py
    :lines: 7-


Backends
^^^^^^^^

The GNU/Linux implementation has multiple backends (see :ref:`backends`), or ways it can take screenshots.  The :py:class:`mss.MSS` constructor will normally autodetect which one is appropriate, but you can override this if you want.

There are three available backends.

:py:mod:`xshmgetimage` (default)
    The fastest backend, based on :c:func:`xcb_shm_get_image`.  It is roughly three times faster than :py:mod:`xgetimage`
    and is used automatically.  When the MIT-SHM extension is unavailable (for example on remote SSH displays), it
    transparently falls back to :py:mod:`xgetimage` so you can always request it safely.

:py:mod:`xgetimage`
    A highly-compatible, but slower, backend based on :c:func:`xcb_get_image`.  Use this explicitly only when you know
    that :py:mod:`xshmgetimage` cannot operate in your environment.

:py:mod:`xlib`
    The legacy backend powered by :c:func:`XGetImage`.  It is kept solely for systems where XCB libraries are
    unavailable and no new features are being added to it.

Command Line
============

You can use ``mss`` via the CLI::

    mss --help

Or via direct call from Python::

    $ python -m mss --help
    usage: mss [-h] [-c COORDINATES] [-l {0,1,2,3,4,5,6,7,8,9}] [-m MONITOR]
           [-o OUTPUT] [--with-cursor] [-q] [-b BACKEND] [-v]

    options:
    -h, --help            show this help message and exit
    -c, --coordinates COORDINATES
                          the part of the screen to capture:
                          TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP;
                          negative TOP or LEFT are insets from the bottom or
                          right edge
    -l, --level {0,1,2,3,4,5,6,7,8,9}
                          the PNG compression level
    -m, --monitor MONITOR
                          the monitor to screenshot
    -o, --output OUTPUT
                          the output file name
    -b, --backend BACKEND
                          platform-specific backend to use
                          (Linux: default/xlib/xgetimage/xshmgetimage; macOS: default; Windows: default/gdi)
    --with-cursor         include the cursor
    -q, --quiet           do not print created files
    -v, --version         show program's version number and exit

.. versionadded:: 3.1.1

.. versionadded:: 8.0.0
    ``--with-cursor`` to include the cursor in screenshots.

.. versionadded:: 10.2.0
    ``--backend`` to force selecting the backend to use.

.. versionadded:: 11.0.0
    ``--coordinates`` now accepts coordinates in the traditional X11 style (WIDTHxHEIGHT+LEFT+TOP), as well as negative
    left or top values (in either style).