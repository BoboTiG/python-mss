.. highlight:: console

==========
Developers
==========

Setup
=====

1. You need to fork the `GitHub repository <https://github.com/BoboTiG/python-mss>`_.
2. Create you own branch.
3. Be sure to add/update tests and documentation within your patch.

Additionnally, you can install `pre-commit <http://pre-commit.com/>`_ to ensure you are doing things well::

    $ python -m pip install --upgrade --user pre-commit
    $ pre-commit install


Testing
=======

Dependency
----------

You will need `pytest <https://pypi.python.org/pypi/pytest>`_::

    $ python -m pip install --upgrade --user pytest


How to Test?
------------

Enable the developer mode::

    $ python -m pip install -e .

Launch the test suit::

    $ python -m pytest tests

.. Note::

    As he module is Python 2 and 3 compliant, do no forgot to test for both. If you cannot, just say it when sending the patch, someone else will validate for you.


Validating the Code
===================

It is important to keep a clean base code. Use tools like `flake8 <https://pypi.python.org/pypi/flake8>`_.


Dependencies
------------

Install required packages::

    $ python -m pip install --upgrade --user flake8


How to Validate?
----------------

::

    $ python -m flake8 .

If there is no output, you are good ;)


Static Type Checking
====================

`mypy <http://mypy-lang.org/>`_ is a compile-time static type checker for Python, allowing optional, gradual typing of Python code.
MSS is using special files syntax for type annotations, which means that type annotations are written inside **pyi** files.


Dependencies
------------

Install required packages::

    $ python -m pip install --upgrade --user mypy-lang


Running Mypy
------------

::

    $ sh check-types.sh -p mss


Documentation
=============

Dependencies
------------

You will need `Sphinx <http://sphinx-doc.org/>`_::

    $ python -m pip install --upgrade --user sphinx


How to Build?
-------------

::

    $ cd docs
    $ make clean html
