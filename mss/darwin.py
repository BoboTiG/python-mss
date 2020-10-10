"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import ctypes
import ctypes.util
import sys
from platform import mac_ver
from typing import TYPE_CHECKING

from .base import MSSBase
from .exception import ScreenShotError
from .screenshot import Size

if TYPE_CHECKING:
    from typing import Any, List, Type, Union  # noqa

    from .models import Monitor, Monitors  # noqa
    from .screenshot import ScreenShot  # noqa

__all__ = ("MSS",)


def cgfloat():
    # type: () -> Union[Type[ctypes.c_double], Type[ctypes.c_float]]
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
    """ Structure that contains information about a rectangle. """

    _fields_ = [("origin", CGPoint), ("size", CGSize)]

    def __repr__(self):
        return "{}<{} {}>".format(type(self).__name__, self.origin, self.size)


class MSS(MSSBase):
    """
    Multiple ScreenShots implementation for macOS.
    It uses intensively the CoreGraphics library.
    """

    __slots__ = {"core", "max_displays"}

    def __init__(self, **_):
        """ macOS initialisations. """

        super().__init__()

        self.max_displays = 32

        self._init_library()
        self._set_cfunctions()

    def _init_library(self):
        """ Load the CoreGraphics library. """
        version = float(".".join(mac_ver()[0].split(".")[:2]))
        if version < 10.16:
            coregraphics = ctypes.util.find_library("CoreGraphics")
        else:
            # macOS Big Sur and newer
            # pylint: disable=line-too-long
            coregraphics = "/System/Library/Frameworks/CoreGraphics.framework/Versions/Current/CoreGraphics"

        if not coregraphics:
            raise ScreenShotError("No CoreGraphics library found.")
        self.core = ctypes.cdll.LoadLibrary(coregraphics)

    def _set_cfunctions(self):
        # type: () -> None
        """ Set all ctypes functions and attach them to attributes. """

        uint32 = ctypes.c_uint32
        void = ctypes.c_void_p
        pointer = ctypes.POINTER
        cfactory = self._cfactory
        core = self.core

        # Note: keep it sorted
        for func, argtypes, restype in (
            ("CGDataProviderCopyData", [void], void),
            ("CGDisplayBounds", [uint32], CGRect),
            ("CGDisplayRotation", [uint32], ctypes.c_float),
            ("CFDataGetBytePtr", [void], void),
            ("CFDataGetLength", [void], ctypes.c_uint64),
            ("CFRelease", [void], void),
            ("CGDataProviderRelease", [void], void),
            (
                "CGGetActiveDisplayList",
                [uint32, pointer(uint32), pointer(uint32)],
                ctypes.c_int32,
            ),
            ("CGImageGetBitsPerPixel", [void], int),
            ("CGImageGetBytesPerRow", [void], int),
            ("CGImageGetDataProvider", [void], void),
            ("CGImageGetHeight", [void], int),
            ("CGImageGetWidth", [void], int),
            ("CGRectStandardize", [CGRect], CGRect),
            ("CGRectUnion", [CGRect, CGRect], CGRect),
            ("CGWindowListCreateImage", [CGRect, uint32, uint32, uint32], void),
        ):
            cfactory(attr=core, func=func, argtypes=argtypes, restype=restype)  # type: ignore

    def _monitors_impl(self):
        # type: () -> None
        """ Get positions of monitors. It will populate self._monitors. """

        int_ = int
        core = self.core

        # All monitors
        # We need to update the value with every single monitor found
        # using CGRectUnion.  Else we will end with infinite values.
        all_monitors = CGRect()
        self._monitors.append({})

        # Each monitors
        display_count = ctypes.c_uint32(0)
        active_displays = (ctypes.c_uint32 * self.max_displays)()
        core.CGGetActiveDisplayList(
            self.max_displays, active_displays, ctypes.byref(display_count)
        )
        rotations = {0.0: "normal", 90.0: "right", -90.0: "left"}
        for idx in range(display_count.value):
            display = active_displays[idx]
            rect = core.CGDisplayBounds(display)
            rect = core.CGRectStandardize(rect)
            width, height = rect.size.width, rect.size.height
            rot = core.CGDisplayRotation(display)
            if rotations[rot] in ["left", "right"]:
                width, height = height, width
            self._monitors.append(
                {
                    "left": int_(rect.origin.x),
                    "top": int_(rect.origin.y),
                    "width": int_(width),
                    "height": int_(height),
                }
            )

            # Update AiO monitor's values
            all_monitors = core.CGRectUnion(all_monitors, rect)

        # Set the AiO monitor's values
        self._monitors[0] = {
            "left": int_(all_monitors.origin.x),
            "top": int_(all_monitors.origin.y),
            "width": int_(all_monitors.size.width),
            "height": int_(all_monitors.size.height),
        }

    def _grab_impl(self, monitor):
        # type: (Monitor) -> ScreenShot
        """ Retrieve all pixels from a monitor. Pixels have to be RGB. """

        # pylint: disable=too-many-locals

        core = self.core
        rect = CGRect(
            (monitor["left"], monitor["top"]), (monitor["width"], monitor["height"])
        )

        image_ref = core.CGWindowListCreateImage(rect, 1, 0, 0)
        if not image_ref:
            raise ScreenShotError("CoreGraphics.CGWindowListCreateImage() failed.")

        width = core.CGImageGetWidth(image_ref)
        height = core.CGImageGetHeight(image_ref)
        prov = copy_data = None
        try:
            prov = core.CGImageGetDataProvider(image_ref)
            copy_data = core.CGDataProviderCopyData(prov)
            data_ref = core.CFDataGetBytePtr(copy_data)
            buf_len = core.CFDataGetLength(copy_data)
            raw = ctypes.cast(data_ref, ctypes.POINTER(ctypes.c_ubyte * buf_len))
            data = bytearray(raw.contents)

            # Remove padding per row
            bytes_per_row = core.CGImageGetBytesPerRow(image_ref)
            bytes_per_pixel = core.CGImageGetBitsPerPixel(image_ref)
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
