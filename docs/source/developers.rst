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

    $ python -m pip install -U pip wheel
    $ python -m pip install -r dev-requirements.txt


How to Test?
------------

Launch the test suit::

    $ python -m pytest

This will test MSS and ensure a good code quality.


Code Quality
============

To ensure the code is always well enough using `flake8 <https://pypi.org/project/flake8/>`_::

    $ ./check.sh


Documentation
=============

To build the documentation, simply type::

    $ sphinx-build -d docs docs/source docs_out --color -W -bhtml
