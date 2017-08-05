# coding: utf-8


def test_get_monitors(sct):
    assert sct.monitors


def test_keys_aio(sct):
    all_monitors = sct.monitors[0]
    assert 'top' in all_monitors
    assert 'left' in all_monitors
    assert 'height' in all_monitors
    assert 'width' in all_monitors


def test_keys_monitor_1(sct):
    mon1 = sct.monitors[1]
    assert 'top' in mon1
    assert 'left' in mon1
    assert 'height' in mon1
    assert 'width' in mon1


def test_dimensions(sct, is_travis):
    mon = sct.monitors[1]
    if not is_travis:
        assert mon['width'] > 0
        assert mon['height'] > 0
    else:
        assert mon['width'] == 1920
        assert mon['height'] == 1440
