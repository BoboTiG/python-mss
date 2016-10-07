#!/usr/bin/env python
# coding: utf-8


def test_attribute_image(mss):
    assert mss.image is None


def test_attribute_monitors(mss):
    assert mss.monitors == []


def test_attribute_width(mss):
    assert mss.width == 0


def test_attribute_height(mss):
    assert mss.height == 0
