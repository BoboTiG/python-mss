# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

# pylint: disable=import-error, too-many-locals

from __future__ import division

import ctypes
import ctypes.util
import sys

from .base import MSSMixin
from .exception import ScreenShotError
from .screenshot import Size

__all__ = ("MSS",)


def cgfloat():
    # type: () -> Any
    """ Get the appropriate value for a float. """

    return ctypes.c_double if sys.maxsize > 2 ** 32 else ctypes.c_float


class CGPoint(ctypes.Structure):
    """ Structure that contains coordinates of a rectangle. """

    _fields_ = [("x", cgfloat()), ("y", cgfloat())]

    def __repr__(self):
        return "{}(left={} top={})".format(type(self).__name__, self.x, self.y)


class CGSize(ctypes.Structure):
    """ Structure that contains dimensions of an rectangle. """

    _fields_ = [("width", cgfloat()), ("height", cgfloat())]

    def __repr__(self):
        return "{}(width={} height={})".format(
            type(self).__name__, self.width, self.height
        )


class CGRect(ctypes.Structure):
    """ Structure that contains informations about a rectangle. """

    _fields_ = [("origin", CGPoint), ("size", CGSize)]

    def __repr__(self):
        return "{}<{} {}>".format(type(self).__name__, self.origin, self.size)


class MSS(MSSMixin):
    """
    Multiple ScreenShots implementation for macOS.
    It uses intensively the CoreGraphics library.
    """

    max_displays = 32  # type: int

    def __init__(self):
        # type: () -> None
        """ macOS initialisations. """

        self._monitors = []  # type: List[Dict[str, int]]

        coregraphics = ctypes.util.find_library("CoreGraphics")
        if not coregraphics:
            raise ScreenShotError("No CoreGraphics library found.")
        self.core = ctypes.cdll.LoadLibrary(coregraphics)

        self._set_cfunctions()

    def _set_cfunctions(self):
        """ Set all ctypes functions and attach them to attributes. """

        def cfactory(attr=self.core, func=None, argtypes=None, restype=None):
            # type: (Any, str, List[Any], Any) -> None
            # pylint: disable=too-many-locals
            """ Factorize ctypes creations. """
            self._cfactory(attr=attr, func=func, argtypes=argtypes, restype=restype)

        uint32 = ctypes.c_uint32
        void = ctypes.c_void_p
        size_t = ctypes.c_size_t
        pointer = ctypes.POINTER

        cfactory(
            func="CGGetActiveDisplayList",
            argtypes=[uint32, pointer(uint32), pointer(uint32)],
            restype=ctypes.c_int32,
        )
        cfactory(func="CGDisplayBounds", argtypes=[uint32], restype=CGRect)
        cfactory(func="CGRectStandardize", argtypes=[CGRect], restype=CGRect)
        cfactory(func="CGRectUnion", argtypes=[CGRect, CGRect], restype=CGRect)
        cfactory(func="CGDisplayRotation", argtypes=[uint32], restype=ctypes.c_float)
        cfactory(
            func="CGWindowListCreateImage",
            argtypes=[CGRect, uint32, uint32, uint32],
            restype=void,
        )
        cfactory(func="CGImageGetWidth", argtypes=[void], restype=size_t)
        cfactory(func="CGImageGetHeight", argtypes=[void], restype=size_t)
        cfactory(func="CGImageGetDataProvider", argtypes=[void], restype=void)
        cfactory(func="CGDataProviderCopyData", argtypes=[void], restype=void)
        cfactory(func="CFDataGetBytePtr", argtypes=[void], restype=void)
        cfactory(func="CFDataGetLength", argtypes=[void], restype=ctypes.c_uint64)
        cfactory(func="CGImageGetBytesPerRow", argtypes=[void], restype=size_t)
        cfactory(func="CGImageGetBitsPerPixel", argtypes=[void], restype=size_t)
        cfactory(func="CGDataProviderRelease", argtypes=[void], restype=void)
        cfactory(func="CFRelease", argtypes=[void], restype=void)

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
            self.core.CGGetActiveDisplayList(
                self.max_displays, active_displays, ctypes.byref(display_count)
            )
            rotations = {0.0: "normal", 90.0: "right", -90.0: "left"}
            for idx in range(display_count.value):
                display = active_displays[idx]
                rect = self.core.CGDisplayBounds(display)
                rect = self.core.CGRectStandardize(rect)
                width, height = rect.size.width, rect.size.height
                rot = self.core.CGDisplayRotation(display)
                if rotations[rot] in ["left", "right"]:
                    width, height = height, width
                self._monitors.append(
                    {
                        "left": int(rect.origin.x),
                        "top": int(rect.origin.y),
                        "width": int(width),
                        "height": int(height),
                    }
                )

                # Update AiO monitor's values
                all_monitors = self.core.CGRectUnion(all_monitors, rect)

            # Set the AiO monitor's values
            self._monitors[0] = {
                "left": int(all_monitors.origin.x),
                "top": int(all_monitors.origin.y),
                "width": int(all_monitors.size.width),
                "height": int(all_monitors.size.height),
            }

        return self._monitors

    def grab(self, monitor):
        # type: (Dict[str, int]) -> ScreenShot
        """
        See :meth:`MSSMixin.grab <mss.base.MSSMixin.grab>` for full details.
        """

        # Convert PIL bbox style
        if isinstance(monitor, tuple):
            monitor = {
                "left": monitor[0],
                "top": monitor[1],
                "width": monitor[2] - monitor[0],
                "height": monitor[3] - monitor[1],
            }

        core = self.core
        rect = CGRect(
            (monitor["left"], monitor["top"]), (monitor["width"], monitor["height"])
        )

        image_ref = core.CGWindowListCreateImage(rect, 1, 0, 0)
        if not image_ref:
            raise ScreenShotError("CoreGraphics.CGWindowListCreateImage() failed.")

        width = int(core.CGImageGetWidth(image_ref))
        height = int(core.CGImageGetHeight(image_ref))
        prov = copy_data = None
        try:
            prov = core.CGImageGetDataProvider(image_ref)
            copy_data = core.CGDataProviderCopyData(prov)
            data_ref = core.CFDataGetBytePtr(copy_data)
            buf_len = core.CFDataGetLength(copy_data)
            raw = ctypes.cast(data_ref, ctypes.POINTER(ctypes.c_ubyte * buf_len))
            data = bytearray(raw.contents)

            # Remove padding per row
            bytes_per_row = int(core.CGImageGetBytesPerRow(image_ref))
            bytes_per_pixel = int(core.CGImageGetBitsPerPixel(image_ref))
            bytes_per_pixel = (bytes_per_pixel + 7) // 8

            if bytes_per_pixel * width != bytes_per_row:
                cropped = bytearray()
                for row in range(height):
                    start = row * bytes_per_row
                    end = start + width * bytes_per_pixel
                    cropped.extend(data[start:end])
                data = cropped
        finally:
            if prov:
                core.CGDataProviderRelease(prov)
            if copy_data:
                core.CFRelease(copy_data)

        return self.cls_image(data, monitor, size=Size(width, height))
