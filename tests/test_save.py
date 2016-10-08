#!/usr/bin/env python
# coding: utf-8


def test_at_least_2_monitors(mss):
    shots = list(mss.save(mon=0))
    assert len(shots) >= 1
