=====
Usage
=====

Import
======

MSS can be used simply as::

    from mss import MSS

    with MSS() as sct:
        # ...

For compatibility with existing code, :py:func:`mss.mss` is still available in
10.2, but deprecated::

    import mss

    with mss.mss() as sct:  # Deprecated in 10.2
        # ...

For compatibility with existing code, platform-specific class names are also
still available in 10.2::

    # GNU/Linux
    from mss.linux import MSS

    # macOS
    from mss.darwin import MSS

    # Microsoft Windows
    from mss.windows import MSS


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

Currently, only the GNU/Linux implementation has multiple backends.  These are described in their own section below.


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
    -c COORDINATES, --coordinates COORDINATES
                          the part of the screen to capture: top, left, width, height
    -l {0,1,2,3,4,5,6,7,8,9}, --level {0,1,2,3,4,5,6,7,8,9}
                          the PNG compression level
    -m MONITOR, --monitor MONITOR
                          the monitor to screenshot
    -o OUTPUT, --output OUTPUT
                          the output file name
    -b, --backend BACKEND
                          platform-specific backend to use
                          (Linux: default/xlib/xgetimage/xshmgetimage; macOS/Windows: default)
    --with-cursor         include the cursor
    -q, --quiet           do not print created files
    -v, --version         show program's version number and exit

.. versionadded:: 3.1.1

.. versionadded:: 8.0.0
    ``--with-cursor`` to include the cursor in screenshots.

.. versionadded:: 10.2.0
    ``--backend`` to force selecting the backend to use.
