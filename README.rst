Python MSS
==========

.. image:: https://travis-ci.org/BoboTiG/python-mss.svg?branch=master
    :target: https://travis-ci.org/BoboTiG/python-mss
.. image:: https://ci.appveyor.com/api/projects/status/72dik18r6b746mb0?svg=true
    :target: https://ci.appveyor.com/project/BoboTiG/python-mss
.. image:: https://img.shields.io/badge/say-thanks-ff69b4.svg
    :target: https://saythanks.io/to/BoboTiG
.. image:: https://pepy.tech/badge/mss
    :target: https://pepy.tech/project/mss
.. image:: https://anaconda.org/conda-forge/python-mss/badges/installer/conda.svg
    :target: https://anaconda.org/conda-forge/python-mss


.. code-block:: python

    from mss import mss

    # The simplest use, save a screen shot of the 1st monitor
    with mss() as sct:
        sct.shot()


An ultra fast cross-platform multiple screenshots module in pure python using ctypes.

- **Python 3.5+** and PEP8 compliant, no dependency, thread-safe;
- very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file;
- but you can use PIL and benefit from all its formats (or add yours directly);
- integrate well with Numpy and OpenCV;
- it could be easily embedded into games and other software which require fast and platform optimized methods to grab screen shots (like AI, Computer Vision);
- get the `source code on GitHub <https://github.com/BoboTiG/python-mss>`_;
- learn with a `bunch of examples <https://python-mss.readthedocs.io/examples.html>`_;
- you can `report a bug <https://github.com/BoboTiG/python-mss/issues>`_;
- need some help? Use the tag *python-mss* on `StackOverflow <https://stackoverflow.com/questions/tagged/python-mss>`_;
- and there is a `complete, and beautiful, documentation <https://python-mss.readthedocs.io>`_ :)
- **MSS** stands for Multiple Screen Shots;


Installation
------------

You can install it with pip::

    python -m pip install -U --user mss

Or you can install it with conda::

    conda install -c conda-forge python-mss

Maintenance
-----------

For the maintainers, here are commands to upload a new release:

    python -m build --sdist --wheel
    twine check dist/*
    twine upload dist/*
