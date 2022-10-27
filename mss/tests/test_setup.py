"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
from subprocess import STDOUT, check_output

from mss import __version__

CMD = "python setup.py sdist bdist_wheel".split()


def test_wheel_python_3_only():
    """Ensure the produced wheel is Python 3 only."""
    output = check_output(CMD, stderr=STDOUT, text=True)
    text = f"mss-{__version__}-py3-none-any.whl"
    assert text in output

    print(output)
    assert "warning" not in output.lower()
