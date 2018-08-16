# coding: utf-8

from __future__ import print_function

import glob
import os

import pytest

import mss


def pytest_addoption(parser):
    txt = 'Display to use (examples: ":0.1", ":0" [default])'
    parser.addoption("--display", action="store", default=":0", help=txt)


def purge_files():
    """ Remove all generated files from previous runs. """

    for fname in glob.glob("*.png"):
        print("Deleting {0!r} ...".format(fname))
        os.unlink(fname)

    for fname in glob.glob("*.png.old"):
        print("Deleting {0!r} ...".format(fname))
        os.unlink(fname)


@pytest.fixture(scope="module", autouse=True)
def before_tests(request):
    request.addfinalizer(purge_files)


@pytest.fixture(scope="session")
def display(request):
    return request.config.getoption("--display")


@pytest.fixture(scope="module")
def sct(display):
    try:
        # `display` keyword is only for GNU/Linux
        return mss.mss(display=display)
    except TypeError:
        return mss.mss()


@pytest.fixture(scope="session")
def is_travis():
    return "TRAVIS" in os.environ


@pytest.fixture(scope="session")
def raw():
    with open("tests/res/monitor-1024x768.raw", "rb") as f:
        yield f.read()
