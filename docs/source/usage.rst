=====
Usage
=====

Import
======

So MSS can be used as simply as::

    from mss import mss

Or import the good one based on your operating system::

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


GNU/Linux
---------

On GNU/Linux, you can specify which display to use (useful for distant screenshots via SSH)::

    with mss(display=":0.0") as sct:
        # ...

A more specific example (only valid on GNU/Linux):

.. literalinclude:: examples/linux_display_keyword.py
    :lines: 8-


Command Line
============

You can use ``mss`` via the CLI::

    mss --help

Or via direct call from Python::

    python -m mss --help

.. versionadded:: 3.1.1
