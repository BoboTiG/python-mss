# coding: utf-8


def test_attributes(sct):
    assert sct.image is None
    assert sct.monitors == []
    assert sct.width == 0
    assert sct.height == 0
