"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
from subprocess import STDOUT, check_call, check_output

from mss import __version__

INSTALL = "python -m build --sdist --wheel".split()
CHECK = "twine check dist/*".split()


def test_wheel_python_3_only():
    """Ensure the produced wheel is Python 3 only."""
    output = check_output(INSTALL, stderr=STDOUT, text=True)
    text = f"mss-{__version__}-py3-none-any.whl"
    assert text in output

    print(output)
    assert "warning" not in output.lower()

    check_call(CHECK)
