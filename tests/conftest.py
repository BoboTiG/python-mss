#!/usr/bin/env python
# coding: utf-8

from os import environ

import pytest

from mss import mss as MSS


def pytest_addoption(parser):
    txt = 'Display to use (examples: ":0.1", ":0" [default])'
    parser.addoption('--display', action='store', default=':0', help=txt)


@pytest.fixture(scope='session')
def display(request):
    return request.config.getoption('--display')


@pytest.fixture(scope='module')
def mss(display):
    try:
        # display keyword is only for GNU/Linux
        return MSS(display=display)
    except TypeError:
        return MSS()


@pytest.fixture(scope='session')
def is_travis():
    return 'TRAVIS' in environ
