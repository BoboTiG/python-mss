=====
Usage
=====

Import
======

MSS can be used as simply as::

    from mss import mss

Or import the good one based on your operating system::

    # GNU/Linux
    from mss.linux import MSS as mss

    # macOS
    from mss.darwin import MSS as mss

    # Microsoft Windows
    from mss.windows import MSS as mss

On GNU/Linux you can also import a specific backend (see :ref:`backends`)
directly when you need a particular implementation, for example::

    from mss.linux.xshmgetimage import MSS as mss


Instance
========

So the module can be used as simply as::

    with mss() as sct:
        # ...

Intensive Use
=============

If you plan to integrate MSS inside your own module or software, pay attention to using it wisely.

This is a bad usage::

    for _ in range(100):
        with mss() as sct:
            sct.shot()

This is a much better usage, memory efficient::

    with mss() as sct:
        for _ in range(100):
            sct.shot()

Also, it is a good thing to save the MSS instance inside an attribute of your class and calling it when needed.


.. _backends:

Backends
--------

Some platforms have multiple ways to take screenshots.  In MSS, these are known as *backends*.  The :py:func:`mss` functions will normally autodetect which one is appropriate for your situation, but you can override this if you want.  For instance, you may know that your specific situation requires a particular backend.

If you want to choose a particular backend, you can use the :py::`backend` keyword to :py:func:`mss`::

    with mss(backend="xgetimage") as sct:
        ...

Alternatively, you can also directly import the backend you want to use::

    from mss.linux.xgetimage import MSS as mss

Currently, only the GNU/Linux implementation has multiple backends.  These are described in their own section below.


GNU/Linux
---------

Display
^^^^^^^

On GNU/Linux, the default display is taken from the :envvar:`DISPLAY` environment variable.  You can instead specify which display to use (useful for distant screenshots via SSH) using the ``display`` keyword::

.. literalinclude:: examples/linux_display_keyword.py
    :lines: 7-


Backends
^^^^^^^^

The GNU/Linux implementation has multiple backends (see :ref:`backends`), or ways it can take screenshots.  The :py:func:`mss.mss` and :py:func:`mss.linux.mss` functions will normally autodetect which one is appropriate, but you can override this if you want.

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
    usage: __main__.py [-h] [-c COORDINATES] [-l {0,1,2,3,4,5,6,7,8,9}]
                    [-m MONITOR] [-o OUTPUT] [-q] [-v] [--with-cursor]

    options:
    -h, --help            show this help message and exit
    -c COORDINATES, --coordinates COORDINATES
                          the part of the screen to capture: top, left, width, height
    -l {0,1,2,3,4,5,6,7,8,9}, --level {0,1,2,3,4,5,6,7,8,9}
                          the PNG compression level
    -m MONITOR, --monitor MONITOR
                          the monitor to screenshot
    -o OUTPUT, --output OUTPUT
                          the output file name
    --with-cursor         include the cursor
    -q, --quiet           do not print created files
    -v, --version         show program's version number and exit

.. versionadded:: 3.1.1

.. versionadded:: 8.0.0
    ``--with-cursor`` to include the cursor in screenshots.
