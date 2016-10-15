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
