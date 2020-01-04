"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from subprocess import check_output

from mss import __version__

CMD = "python setup.py sdist bdist_wheel".split()


def test_wheel_python_3_only():
    """Ensure the produced wheel is Python 3 only."""
    output = str(check_output(CMD))
    text = "mss-{}-py3-none-any.whl".format(__version__)
    assert text in output
