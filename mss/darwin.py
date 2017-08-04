# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

# pylint: disable=import-error

from __future__ import division

import ctypes
import ctypes.util
import math
import sys

from .base import MSSBase
from .exception import ScreenShotError

__all__ = ['MSS']


def cgfloat():
    # type: () -> Any
    """ Get the appropriate value for a float. """

    return ctypes.c_double if sys.maxsize > 2 ** 32 else ctypes.c_float


class CGPoint(ctypes.Structure):
    """ Structure that contains coordinates of a rectangle. """

    _fields_ = [('x', cgfloat()), ('y', cgfloat())]

    def __repr__(self):
        return '{0}(left={cls.x} top={cls.y})'.format(
            type(self).__name__, cls=self)


class CGSize(ctypes.Structure):
    """ Structure that contains dimensions of an rectangle. """

    _fields_ = [('width', cgfloat()), ('height', cgfloat())]

    def __repr__(self):
        return '{0}(width={cls.width} height={cls.height})'.format(
            type(self).__name__, cls=self)


class CGRect(ctypes.Structure):
    """ Structure that contains informations about a rectangle. """

    _fields_ = [('origin', CGPoint), ('size', CGSize)]

    def __repr__(self):
        return '{0}<{cls.origin} {cls.size}>'.format(
            type(self).__name__, cls=self)


class MSS(MSSBase):
    """
    Multiple ScreenShots implementation for macOS.
    It uses intensively the CoreGraphics library.
    """

    max_displays = 32  # type: int

    def __init__(self):
        # type: () -> None
        """ macOS initialisations. """

        coregraphics = ctypes.util.find_library('CoreGraphics')
        if not coregraphics:
            raise ScreenShotError('No CoreGraphics library found.', locals())
        self.core = ctypes.cdll.LoadLibrary(coregraphics)

        self._set_argtypes()
        self._set_restypes()

    def _set_argtypes(self):
        # type: () -> None
        """ Functions arguments. """

        self.core.CGGetActiveDisplayList.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32)]
        self.core.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        self.core.CGRectStandardize.argtypes = [CGRect]
        self.core.CGRectUnion.argtypes = [CGRect, CGRect]
        self.core.CGDisplayRotation.argtypes = [ctypes.c_uint32]
        self.core.CGWindowListCreateImage.argtypes = [
            CGRect,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32]
        self.core.CGImageGetDataProvider.argtypes = [ctypes.c_void_p]
        self.core.CGDataProviderCopyData.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetLength.argtypes = [ctypes.c_void_p]
        self.core.CGDataProviderRelease.argtypes = [ctypes.c_void_p]

    def _set_restypes(self):
        # type: () -> None
        """ Functions return type. """

        self.core.CGGetActiveDisplayList.restype = ctypes.c_int32
        self.core.CGDisplayBounds.restype = CGRect
        self.core.CGRectStandardize.restype = CGRect
        self.core.CGRectUnion.restype = CGRect
        self.core.CGDisplayRotation.restype = ctypes.c_float
        self.core.CGWindowListCreateImage.restype = ctypes.c_void_p
        self.core.CGImageGetDataProvider.restype = ctypes.c_void_p
        self.core.CGDataProviderCopyData.restype = ctypes.c_void_p
        self.core.CFDataGetBytePtr.restype = ctypes.c_void_p
        self.core.CFDataGetLength.restype = ctypes.c_uint64
        self.core.CGDataProviderRelease.restype = ctypes.c_void_p

    @property
    def monitors(self):
        # type: () -> List[Dict[str, int]]
        """ Get positions of monitors (see parent class). """

        if not self._monitors:
            # All monitors
            # We need to update the value with every single monitor found
            # using CGRectUnion.  Else we will end with infinite values.
            all_monitors = CGRect()
            self._monitors.append({})

            # Each monitors
            display_count = ctypes.c_uint32(0)
            active_displays = (ctypes.c_uint32 * self.max_displays)()
            self.core.CGGetActiveDisplayList(self.max_displays,
                                             active_displays,
                                             ctypes.byref(display_count))
            rotations = {0.0: 'normal', 90.0: 'right', -90.0: 'left'}
            for idx in range(display_count.value):
                display = active_displays[idx]
                rect = self.core.CGDisplayBounds(display)
                rect = self.core.CGRectStandardize(rect)
                width, height = rect.size.width, rect.size.height
                rot = self.core.CGDisplayRotation(display)
                if rotations[rot] in ['left', 'right']:
                    width, height = height, width
                self._monitors.append({
                    'left': int(rect.origin.x),
                    'top': int(rect.origin.y),
                    'width': int(width),
                    'height': int(height),
                })

                # Update AiO monitor's values
                all_monitors = self.core.CGRectUnion(all_monitors, rect)

            # Update AiO monitor's values
            self._monitors[0] = {
                'left': int(all_monitors.origin.x),
                'top': int(all_monitors.origin.y),
                'width': int(all_monitors.size.width),
                'height': int(all_monitors.size.height),
            }

        return self._monitors

    def grab(self, monitor):
        # type: (Dict[str, int]) -> ScreenShot
        """
        See :meth:`MSSBase.grab <mss.base.MSSBase.grab>` for full details.

        When the monitor width is not divisible by 16, its width is reduced
        to the previous number divisible by 16.  So we need to add extra
        black pixels.
        """

        rounded_width = int(math.ceil(monitor['width'] // 16) * 16)

        rect = CGRect((monitor['left'], monitor['top']),
                      (rounded_width, monitor['height']))

        image_ref = self.core.CGWindowListCreateImage(rect, 1, 0, 0)
        if not image_ref:
            raise ScreenShotError(
                'CoreGraphics.CGWindowListCreateImage() failed.', locals())

        prov = self.core.CGImageGetDataProvider(image_ref)
        data = self.core.CGDataProviderCopyData(prov)
        data_ref = self.core.CFDataGetBytePtr(data)
        buf_len = self.core.CFDataGetLength(data)
        data = ctypes.cast(data_ref, ctypes.POINTER(ctypes.c_ubyte * buf_len))
        data = data.contents
        self.core.CGDataProviderRelease(prov)

        if rounded_width != monitor['width']:
            data = self.resize(data, monitor)

        return self.cls_image(data, monitor)

    @staticmethod
    def resize(data, monitor):
        # type: (bytearray, Dict[str, int]) -> bytearray
        """ Extend a 16 width-rounded screenshot to its original width. """

        rounded_width = int(math.ceil(monitor['width'] // 16) * 16)
        cropped = bytearray()

        for row in range(monitor['height']):
            start = row * rounded_width * 4
            end = start + monitor['width'] * 4
            cropped.extend(data[start:end])

        cropped.extend(b'\00' * (monitor['width'] - rounded_width) * 4)

        return cropped
