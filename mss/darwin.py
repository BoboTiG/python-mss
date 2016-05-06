#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

# pylint: disable=import-error

from sys import maxsize
from ctypes import (
    POINTER, Structure, sizeof, c_double, byref, c_char_p, c_int, c_int32, c_long, c_uint,
    c_uint32, c_float, c_ulong, c_ushort, c_void_p, cast, cdll, create_string_buffer)
from ctypes.util import find_library

from .base import MSSBase
from .exception import ScreenshotError

from Quartz import CGDisplayBounds as t

__all__ = ['MSS']


CGFloat = c_double if maxsize > 2 ** 32 else c_float


class CGPoint(Structure):
    ''' Structure that contains coordinates of an image. '''

    _fields_ = [('x', CGFloat), ('y', CGFloat)]


class CGSize(Structure):
    ''' Structure that contains dimensions of an image. '''

    _fields_ = [('width', CGFloat), ('height', CGFloat)]


class CGRect(Structure):
    ''' Structure that contains informations about an image. '''

    _fields_ = [('origin', CGPoint), ('size', CGSize)]

    def __rrepr__(self):
        ''' Without this method, segfault. Segfault everywhere! '''

        ret = (self.origin.x, self.origin.y, self.size.width, self.size.height)
        return ret.__repr__()


class MSS(MSSBase):
    ''' Mutliple ScreenShots implementation for MacOS X.
        It uses intensively the Quartz.
    '''

    max_displays = 32  # Could be augmented, if needed ...

    def __init__(self, display=None):
        ''' MacOS X initialisations. '''

        coregraphics = find_library('CoreGraphics')
        if not coregraphics:
            raise ScreenshotError('No CoreGraphics library found.')
        self.cgs = cdll.LoadLibrary(coregraphics)

        self._set_argtypes()
        self._set_restypes()

    def _set_argtypes(self):
        ''' Functions arguments. '''

        self.cgs.CGGetActiveDisplayList.argtypes = \
            [c_uint32, POINTER(c_uint32), POINTER(c_uint32)]
        self.cgs.CGDisplayBounds.argtypes = [c_uint32]
        #self.cgs.CGRectStandardize.argtypes = []
        #self.cgs..argtypes = []
        #self.cgs..argtypes = []

    def _set_restypes(self):
        ''' Functions return type. '''

        self.cgs.CGGetActiveDisplayList.restypes = c_int32
        self.cgs.CGDisplayBounds.restypes = CGRect
        #self.cgs.CGRectStandardize.restypes =
        #self.cgs..restypes =
        #self.cgs..restypes =

    def enum_display_monitors(self, force=False):
        ''' Get positions of monitors (see parent class). '''

        if not self.monitors or force:
            # All monitors
            self.monitors.append({
                b'left': int(get_infinity('min')),
                b'top': int(get_infinity('min')),
                b'width': int(get_infinity('max')),
                b'height': int(get_infinity('max'))
            })

            # Each monitors
            display_count = c_uint32(0)
            active_displays = (c_uint32 * self.max_displays)()
            self.cgs.CGGetActiveDisplayList(self.max_displays, active_displays,
                                            byref(display_count))
            rotations = {0.0: 'normal', 90.0: 'right', -90.0: 'left'}
            for idx in range(display_count.value):
                display = c_uint32(active_displays[idx])

                rect = self.cgs.CGDisplayBounds(display) # SEGFAULT HERE!!!!
                print(rect)
                print(t(display))

                rect = self.cgs.CGRectStandardize(CGDisplayBounds(display))
                left, top = rect.origin.x, rect.origin.y
                width, height = rect.size.width, rect.size.height
                rot = CGDisplayRotation(display)
                if rotations[rot] in ['left', 'right']:
                    width, height = height, width
                self.monitors.append({
                    b'left': int(left),
                    b'top': int(top),
                    b'width': int(width),
                    b'height': int(height)
                })

        return self.monitors

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB. '''

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        rect = CGRect((left, top), (width, height))
        options = kCGWindowListOptionOnScreenOnly
        winid = kCGNullWindowID
        default = kCGWindowImageDefault

        image_ref = CGWindowListCreateImage(rect, options, winid, default)
        if not image_ref:
            raise ScreenshotError('CGWindowListCreateImage() failed.')

        self.width = CGImageGetWidth(image_ref)
        self.height = CGImageGetHeight(image_ref)
        image_data = CGDataProviderCopyData(CGImageGetDataProvider(image_ref))

        # Replace pixels values: BGRA to RGB.
        image_data = bytearray(image_data)
        image = bytearray(self.height * self.width * 3)
        image[0::3], image[1::3], image[2::3] = \
            image_data[2::4], image_data[1::4], image_data[0::4]
        self.image = bytes(image)
        return self.image


def get_infinity(what='all'):
    ''' Get infinity "numbers". '''

    min_ = -8.988465674311579e+307
    max_ = 1.7976931348623157e+308
    if what == 'min':
        return min_
    elif what == 'max':
        return max_
    return (min_, max_)
