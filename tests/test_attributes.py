#!/usr/bin/env python
# coding: utf-8


def test_attribute_image(sct):
    assert sct.image is None


def test_attribute_monitors(sct):
    assert sct.monitors == []


def test_attribute_width(sct):
    assert sct.width == 0


def test_attribute_height(sct):
    assert sct.height == 0
