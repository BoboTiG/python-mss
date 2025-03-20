Welcome to Python MSS's documentation!
======================================

|PyPI Version|
|PyPI Status|
|PyPI Python Versions|
|GitHub Build Status|
|GitHub License|

|Patreon|

.. code-block:: python

    from mss import mss

    # The simplest use, save a screenshot of the 1st monitor
    with mss() as sct:
        sct.shot()


An ultra fast cross-platform multiple screenshots module in pure python using ctypes.

    - **Python 3.9+**, :pep:`8` compliant, no dependency, thread-safe;
    - very basic, it will grab one screenshot by monitor or a screenshot of all monitors and save it to a PNG file;
    - but you can use PIL and benefit from all its formats (or add yours directly);
    - integrate well with Numpy and OpenCV;
    - it could be easily embedded into games and other software which require fast and platform optimized methods to grab screenshots (like AI, Computer Vision);
    - get the `source code on GitHub <https://github.com/BoboTiG/python-mss>`_;
    - learn with a `bunch of examples <https://python-mss.readthedocs.io/examples.html>`_;
    - you can `report a bug <https://github.com/BoboTiG/python-mss/issues>`_;
    - need some help? Use the tag *python-mss* on `Stack Overflow <https://stackoverflow.com/questions/tagged/python-mss>`_;
    - **MSS** stands for Multiple ScreenShots;

+-------------------------+
|         Content         |
+-------------------------+
|.. toctree::             |
|   :maxdepth: 1          |
|                         |
|   installation          |
|   usage                 |
|   examples              |
|   support               |
|   api                   |
|   developers            |
|   where                 |
+-------------------------+

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. |PyPI Version| image:: https://img.shields.io/pypi/v/mss.svg
   :target: https://pypi.python.org/pypi/mss/
.. |PyPI Status| image:: https://img.shields.io/pypi/status/mss.svg
   :target: https://pypi.python.org/pypi/mss/
.. |PyPI Python Versions| image:: https://img.shields.io/pypi/pyversions/mss.svg
   :target: https://pypi.python.org/pypi/mss/
.. |Github Build Status| image:: https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml/badge.svg?branch=main
   :target: https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml
.. |GitHub License| image:: https://img.shields.io/github/license/BoboTiG/python-mss.svg
   :target: https://github.com/BoboTiG/python-mss/blob/main/LICENSE.txt
.. |Patreon| image:: https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white
   :target: https://www.patreon.com/mschoentgen
