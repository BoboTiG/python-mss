#!/usr/bin/env python
# coding: utf-8

from contextlib import contextmanager
from time import time


@contextmanager
def timer(msg):
    ''' A little timer. '''

    start = time()
    yield
    print('{}: {} sec'.format(msg, time() - start))
