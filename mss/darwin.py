#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

# pylint: disable=import-error

from sys import maxsize
from ctypes import (
    POINTER, Structure, c_double, byref, c_int32, c_long, c_uint32, c_float,
    c_void_p, cast, cdll)
from ctypes.util import find_library

from .base import MSSBase
from .exception import ScreenshotError

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

from Quartz import kCGWindowListOptionOnScreenOnly as t
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
        self.cgs.CGRectStandardize.argtypes = [CGRect]
        self.cgs.CGDisplayRotation.argtypes = [c_uint32]
        self.cgs.CGWindowListCreateImage.argtypes = [CGRect, c_uint32, c_uint32, c_uint32]
        self.cgs.CGImageGetWidth.argtypes = [c_void_p]
        self.cgs.CGImageGetHeight.argtypes = [c_void_p]
        self.cgs.CGImageGetDataProvider.argtypes = [c_void_p]
        self.cgs.CGDataProviderCopyData.argtypes = [c_void_p]

    def _set_restypes(self):
        ''' Functions return type. '''

        self.cgs.CGGetActiveDisplayList.restype = c_int32
        self.cgs.CGDisplayBounds.restype = CGRect
        self.cgs.CGRectStandardize.restype = CGRect
        self.cgs.CGDisplayRotation.restype = c_float
        self.cgs.CGWindowListCreateImage.restype = c_void_p
        self.cgs.CGImageGetWidth.restype = CGFloat
        self.cgs.CGImageGetHeight.restype = CGFloat
        self.cgs.CGImageGetDataProvider.restype = c_void_p
        #self.cgs.CGDataProviderCopyData.restype = POINTER(c_ubyte)

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
                display = active_displays[idx]

                rect = self.cgs.CGDisplayBounds(display)
                rect = self.cgs.CGRectStandardize(rect)
                left, top = rect.origin.x, rect.origin.y
                width, height = rect.size.width, rect.size.height
                rot = self.cgs.CGDisplayRotation(display)
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

        image_ref = self.cgs.CGWindowListCreateImage(rect, 1, 0, 0)
        if not image_ref:
            err = 'CoreGraphics.CGWindowListCreateImage() failed.'
            raise ScreenshotError(err)

        self.width = int(self.cgs.CGImageGetWidth(image_ref))
        self.height = int(self.cgs.CGImageGetHeight(image_ref))
        data_provider = self.cgs.CGImageGetDataProvider(image_ref)


        from ctypes import string_at, c_char, create_string_buffer
        buf_len = self.height * self.width * 4
        self.cgs.CGDataProviderCopyData.restype = POINTER(c_void_p)
        image_data = self.cgs.CGDataProviderCopyData(data_provider)
        print(string_at(image_data), type(image_data.contents))
        image_data = create_string_buffer(image_data)

        # Replace pixels values: BGRA to RGB.
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
