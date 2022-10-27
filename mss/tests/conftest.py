"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import glob
import os

import pytest

import mss


@pytest.fixture(autouse=True)
def no_warnings(recwarn):
    """Fail on warning."""

    yield

    warnings = [
        "{w.filename}:{w.lineno} {w.message}".format(w=warning) for warning in recwarn
    ]
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


@pytest.fixture(scope="module")
def sct():
    try:
        # `display` kwarg is only for GNU/Linux
        return mss.mss(display=os.getenv("DISPLAY"))
    except TypeError:
        return mss.mss()


@pytest.fixture(scope="session")
def is_travis():
    return "TRAVIS" in os.environ


@pytest.fixture(scope="session")
def raw():
    here = os.path.dirname(__file__)
    file = os.path.join(here, "res", "monitor-1024x768.raw")
    with open(file, "rb") as f:
        yield f.read()


@pytest.fixture(scope="module")
def pixel_ratio(sct):
    """Get the pixel, used to adapt test checks."""
    # Grab a 1x1 screenshot
    region = {"top": 0, "left": 0, "width": 1, "height": 1}

    # On macOS with Retina display, the width will be 2 instead of 1
    return sct.grab(region).size[0]
