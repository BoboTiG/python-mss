#!/usr/bin/env python
# coding: utf-8


def test_get_monitors(mss):
    monitors = mss.enum_display_monitors()
    assert monitors is mss.monitors
    assert monitors


def test_keys_aio(mss):
    all_monitors = mss.monitors[0]
    assert 'top' in all_monitors
    assert 'left' in all_monitors
    assert 'height' in all_monitors
    assert 'width' in all_monitors


def test_keys_monitor_1(mss):
    mon1 = mss.monitors[1]
    assert 'top' in mon1
    assert 'left' in mon1
    assert 'height' in mon1
    assert 'width' in mon1


def test_dimensions(mss, is_travis):
    width = 1280 if is_travis else 0
    height = 1024 if is_travis else 0
    for mon in mss.monitors:
        assert mon['width'] >= width
        assert mon['height'] >= height


def test_get_monitors_force(mss):
    monitors = mss.enum_display_monitors(force=True)
    assert monitors is mss.monitors
    assert monitors
