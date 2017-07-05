Python MSS
==========

.. image:: https://travis-ci.org/BoboTiG/python-mss.svg?branch=dev
    :target: https://travis-ci.org/BoboTiG/python-mss


    from mss import mss


    # The simplest use, save a screenshot of the 1st monitor
    with mss() as sct:
        sct.shot()


An ultra fast cross-platform multiple screenshots module in pure python using ctypes.

- **Python 2 & 3** and PEP8 compliant, no dependency;
- very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file;
- but you can use PIL and benefit from all its formats (or add yours directly);
- integrate well with Numpy and OpenCV;
- it could be easily embedded into games and other softwares which require fast and plateforme optimized methods to grab screenshots;
- get the `source code on GitHub <https://github.com/BoboTiG/python-mss>`_;
- learn with a `bunch of examples <https://github.com/BoboTiG/python-mss/tree/master/examples>`_;
- you can `report a bug <https://github.com/BoboTiG/python-mss/issues>`_;
- and there is a `complete, and beautiful, documentation <https://python-mss.readthedocs.io>`_ :)
- **MSS** stands for Multiple ScreenShots;


Installation
------------

You can install it with pip::

    pip install --upgrade mss
