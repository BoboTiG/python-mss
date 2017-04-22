# coding: utf-8

import pytest


def test_bad_length(sct):
    sct.width = 1024
    sct.height = 768
    with pytest.raises(ValueError):
        sct.bgra_to_rgb(bytearray(b'789c626001000000ffff030000060005'))


def test_good_bytes(sct, raw):
    sct.width = 1024
    sct.height = 768
    image = sct.bgra_to_rgb(raw)
    assert isinstance(image, bytes)


def test_good_bytearray(sct, raw):
    sct.width = 1024
    sct.height = 768
    image = sct.bgra_to_rgb(bytearray(raw))
    assert isinstance(image, bytes)
