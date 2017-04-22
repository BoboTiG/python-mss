# coding: utf-8

from os import environ

import pytest

from mss import mss


def pytest_addoption(parser):
    txt = 'Display to use (examples: ":0.1", ":0" [default])'
    parser.addoption('--display', action='store', default=':0', help=txt)


@pytest.fixture(scope='session')
def display(request):
    return request.config.getoption('--display')


@pytest.fixture(scope='module')
def sct(display):
    try:
        # display keyword is only for GNU/Linux
        return mss(display=display)
    except TypeError:
        return mss()


@pytest.fixture(scope='session')
def is_travis():
    return 'TRAVIS' in environ


@pytest.fixture(scope='session')
def raw():
    return open('tests/monitor-1024x768.raw', 'rb').read()
