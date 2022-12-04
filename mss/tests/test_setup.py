"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import platform
from subprocess import STDOUT, check_call, check_output

import pytest

from mss import __version__

if platform.system().lower() != "linux":
    pytestmark = pytest.mark.skip

# Note: using `--no-isolation` because it doesn't work with `tox`
INSTALL = "python -m build --no-isolation --sdist --wheel".split()
CHECK = "twine check dist/*".split()


def test_wheel_python_3_only():
    """Ensure the produced wheel is Python 3 only."""
    output = str(check_output(INSTALL, stderr=STDOUT))
    text = f"Successfully built mss-{__version__}.tar.gz and mss-{__version__}-py3-none-any.whl"
    assert text in output

    check_call(CHECK)
