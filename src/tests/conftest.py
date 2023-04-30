"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import glob
import os
from hashlib import md5
from pathlib import Path
from zipfile import ZipFile

import pytest


@pytest.fixture(autouse=True)
def no_warnings(recwarn):
    """Fail on warning."""

    yield

    warnings = ["{w.filename}:{w.lineno} {w.message}".format(w=warning) for warning in recwarn]
    for warning in warnings:
        print(warning)
    assert not warnings


def purge_files():
    """Remove all generated files from previous runs."""

    for fname in glob.glob("*.png"):
        print("Deleting {!r} ...".format(fname))
        os.unlink(fname)

    for fname in glob.glob("*.png.old"):
        print("Deleting {!r} ...".format(fname))
        os.unlink(fname)


@pytest.fixture(scope="module", autouse=True)
def before_tests(request):
    request.addfinalizer(purge_files)


@pytest.fixture(scope="session")
def raw() -> bytes:
    file = Path(__file__).parent / "res" / "monitor-1024x768.raw.zip"
    with ZipFile(file) as fh:
        data = fh.read(file.with_suffix("").name)

    assert md5(data).hexdigest() == "125696266e2a8f5240f6bc17e4df98c6"
    return data
