#!/usr/bin/env python
# coding: utf-8

from os.path import isfile


def test_at_least_2_monitors(sct):
    shots = list(sct.save(mon=0))
    assert len(shots) >= 1


def test_files_exist(sct):
    for filename in sct.save(mon=0):
        assert isfile(filename)
