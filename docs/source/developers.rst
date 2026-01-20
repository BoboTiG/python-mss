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
    $ python -m pip install -e '.[tests]'


How to Test?
------------

Launch the test suite::

    $ python -m pytest


Code Quality
============

To ensure the code quality is correct enough::

    $ python -m pip install -e '.[dev]'
    $ ./check.sh  # Linux/macOS
    $ .\check.ps1  # Windows (PowerShell)


Documentation
=============

To build the documentation, simply type::

    $ python -m pip install -e '.[docs]'
    $ sphinx-build -d docs docs/source docs_out --color -W -bhtml


XCB Code Generator
==================

.. versionadded:: 10.2.0

The GNU/Linux XCB backends rely on generated ctypes bindings.  If you need to
add new XCB requests or types, do **not** edit ``src/mss/linux/xcbgen.py`` by
hand.  Instead, follow the workflow described in ``src/xcbproto/README.md``,
which explains how to update ``gen_xcb_to_py.py`` and regenerate the bindings.
