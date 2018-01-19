=====
Usage
=====

Import
======

So MSS can be used as simply as::

    from mss import mss


Or import the good one base on your operating system::

    # MacOS X
    from mss.darwin import MSS as mss

    # GNU/Linux
    from mss.linux import MSS as mss

    # Microsoft Windows
    from mss.windows import MSS as mss


Instance
========

So the module can be used as simply as::

    with mss() as sct:
        # ...

Or::

    sct = mss()


PNG Compression
---------------

You can tweak the PNG compression level (see :py:func:`zlib.compress()` for details)::

    sct.compression_level = 2

.. versionadded:: 3.1.3


GNU/Linux
---------

On GNU/Linux, you can specify which display to use (useful for distant screenshots via SSH)::

    with mss(display=':0.0') as sct:
        # ...

A more specific example to only target GNU/Linux:

.. literalinclude:: examples/linux_display_keyword.py
    :lines: 9-


Command line
============

You can use ``mss`` via the CLI:

    mss --help

Or via direct call from Python:

    python -m mss --help

.. versionadded:: 3.1.1
