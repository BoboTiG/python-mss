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

You will need `tox <https://pypi.org/project/tox/>`_::

    $ python -m pip install --upgrade --user tox


How to Test?
------------

Launch the test suit::

    $ tox

    # or
    $ TOXENV=py37 tox

This will test MSS and ensure a good code quality.


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

To build the documentation, simply type::

    $ TOXENV=docs tox
