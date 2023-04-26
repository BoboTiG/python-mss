.. highlight:: console

==========
Developers
==========

Setup
=====

1. You need to fork the `GitHub repository <https://github.com/BoboTiG/python-mss>`_.
2. Create you own branch.
3. Be sure to add/update tests and documentation within your patch.


Testing
=======

Dependency
----------

You will need `pytest <https://pypi.org/project/pytest/>`_::

    $ python -m venv venv
    $ . venv/bin/activate
    $ python -m pip install -U pip
    $ python -m pip install -e '.[test]'


How to Test?
------------

Launch the test suit::

    $ python -m pytest


Code Quality
============

To ensure the code quality is correct enough::

    $ python -m pip install -e '.[dev]'
    $ ./check.sh


Documentation
=============

To build the documentation, simply type::

    $ sphinx-build -d docs docs/source docs_out --color -W -bhtml
