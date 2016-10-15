==========
Developers
==========

Setup
=====

1. You need to fork the `GitHub repository <https://github.com/BoboTiG/python-mss>`_.

    **Note :** always work on a **specific branch**, based on the *dev* one, dedicated to your patch.

2. Be sure to add/update tests and documentation within your patch.


Testing
=======

As he module is Python 2 and 3 compliant, do no forgot to test for both. If you cannot, just say it when sending the patch, someone else will validate for you.


Dependency
----------

You will need `pytest <https://pypi.python.org/pypi/pytest>`_::

    pip install pytest


How to test?
------------

Enable the developer mode::

    sudo python setup.py develop

Lauch the test suit::

    py.test


Validating the code
===================

It is important to keep a clean base code. Use tools like `flake8 <https://pypi.python.org/pypi/flake8>`_ and `Pylint <https://pypi.python.org/pypi/pylint>`_.


Dependencies
------------

Install required packages::

    pip install flake8 pylint


How to validate?
----------------

::

    flake8
    pylint mss

If there is no output, you are good ;)


Static type checking
====================

`mypy <http://mypy-lang.org/>`_ is a compile-time static type checker for Python, allowing optional, gradual typing of Python code.
MSS is using special files syntax for type annotations, which means that type annotations are written inside **pyi** files.


Dependencies
------------

Install required packages::

    pip install mypy-lang


Running mypy
------------

::

    mypy --check-untyped-defs --warn-incomplete-stub -m mss
    mypy --check-untyped-defs --warn-incomplete-stub mss


Documentation
=============

Dependencies
------------

You will need `Sphinx <http://sphinx-doc.org/>`_::

    pip install sphinx


How to build?
-------------

::

    cd docs
    make clean html
