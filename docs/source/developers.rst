.. highlight:: console

==========
Developers
==========

Setup
=====

1. You need to fork the `GitHub repository <https://github.com/BoboTiG/python-mss>`_.
2. Create you own branch.
3. Be sure to add/update tests and documentation within your patch.

Additionally, you can install `pre-commit <http://pre-commit.com/>`_ to ensure you are doing things well::

    $ python -m pip install -U --user pre-commit
    $ pre-commit install


Testing
=======

Dependency
----------

You will need `tox <https://pypi.org/project/tox/>`_::

    $ python -m pip install -U --user tox


How to Test?
------------

Launch the test suit::

    $ tox

    # or
    $ TOXENV=py37 tox

This will test MSS and ensure a good code quality.


Code Quality
============

To ensure the code is always well enough using `flake8 <https://pypi.org/project/flake8/>`_::

    $ TOXENV=lint tox


Static Type Checking
====================

To check type annotation using `mypy <http://mypy-lang.org/>`_::

    $ TOXENV=types tox


Documentation
=============

To build the documentation, simply type::

    $ TOXENV=docs tox
