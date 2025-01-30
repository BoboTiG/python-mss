"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
from ctypes import (
    POINTER,
    Structure,
    c_bool,
    c_char_p,
    c_double,
    c_float,
    c_int32,
    c_long,
    c_ubyte,
    c_uint32,
    c_uint64,
    c_void_p,
)
from platform import mac_ver
from typing import TYPE_CHECKING, Any

from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot, Size

if TYPE_CHECKING:  # pragma: nocover
    from mss.models import CConstants, CFunctions, Monitor, Window

__all__ = ("MSS",)

MAC_VERSION_CATALINA = 10.16


def cgfloat() -> type[c_double | c_float]:
    """Get the appropriate value for a float."""
    return c_double if sys.maxsize > 2**32 else c_float


class CGPoint(Structure):
    """Structure that contains coordinates of a rectangle."""

    _fields_ = (("x", cgfloat()), ("y", cgfloat()))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(left={self.x} top={self.y})"


class CGSize(Structure):
    """Structure that contains dimensions of an rectangle."""

    _fields_ = (("width", cgfloat()), ("height", cgfloat()))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(width={self.width} height={self.height})"


class CGRect(Structure):
    """Structure that contains information about a rectangle."""

    _fields_ = (("origin", CGPoint), ("size", CGSize))

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.origin} {self.size}>"


# C functions that will be initialised later.
#
# Available attr: core.
#
# Note: keep it sorted by cfunction.
CFUNCTIONS: CFunctions = {
    # Syntax: cfunction: (attr, argtypes, restype)
    "CGDataProviderCopyData": ("core", [c_void_p], c_void_p),
    "CGDisplayBounds": ("core", [c_uint32], CGRect),
    "CGDisplayRotation": ("core", [c_uint32], c_float),
    "CFDataGetBytePtr": ("core", [c_void_p], c_void_p),
    "CFDataGetLength": ("core", [c_void_p], c_uint64),
    "CFRelease": ("core", [c_void_p], c_void_p),
    "CGDataProviderRelease": ("core", [c_void_p], c_void_p),
    "CGGetActiveDisplayList": ("core", [c_uint32, POINTER(c_uint32), POINTER(c_uint32)], c_int32),
    "CGImageGetBitsPerPixel": ("core", [c_void_p], int),
    "CGImageGetBytesPerRow": ("core", [c_void_p], int),
    "CGImageGetDataProvider": ("core", [c_void_p], c_void_p),
    "CGImageGetHeight": ("core", [c_void_p], int),
    "CGImageGetWidth": ("core", [c_void_p], int),
    "CGRectStandardize": ("core", [CGRect], CGRect),
    "CGRectUnion": ("core", [CGRect, CGRect], CGRect),
    "CGWindowListCreateImage": ("core", [CGRect, c_uint32, c_uint32, c_uint32], c_void_p),
    "CGWindowListCopyWindowInfo": ("core", [c_uint32, c_uint32], c_void_p),
    "CFArrayGetCount": ("core", [c_void_p], c_uint64),
    "CFArrayGetValueAtIndex": ("core", [c_void_p, c_uint64], c_void_p),
    "CFNumberGetValue": ("core", [c_void_p, c_int32, c_void_p], c_bool),
    "CFStringGetCString": ("core", [c_void_p, c_char_p, c_long, c_uint32], c_bool),
    "CFDictionaryGetValue": ("core", [c_void_p, c_void_p], c_void_p),
    "CGRectMakeWithDictionaryRepresentation": ("core", [c_void_p, POINTER(CGRect)], c_bool),
}

CCONSTANTS: CConstants = {
    # Syntax: cconstant: type or value
    "kCGWindowNumber": c_void_p,
    "kCGWindowName": c_void_p,
    "kCGWindowOwnerName": c_void_p,
    "kCGWindowBounds": c_void_p,
    "kCGWindowListOptionOnScreenOnly": 0b0001,
    "kCGWindowListOptionIncludingWindow": 0b1000,
    "kCFStringEncodingUTF8": 0x08000100,
    "kCGNullWindowID": 0,
    "kCFNumberSInt32Type": 3,
    "kCGWindowImageBoundsIgnoreFraming": 0b0001,
    "CGRectNull": CGRect,
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for macOS.
    It uses intensively the CoreGraphics library.
    """

    __slots__ = {"constants", "core", "max_displays"}

    def __init__(self, /, **kwargs: Any) -> None:
        """MacOS initialisations."""
        super().__init__(**kwargs)

        self.max_displays = kwargs.get("max_displays", 32)

        self._init_library()
        self._set_cfunctions()
        self._set_cconstants()

    def _init_library(self) -> None:
        """Load the CoreGraphics library."""
        version = float(".".join(mac_ver()[0].split(".")[:2]))
        if version < MAC_VERSION_CATALINA:
            coregraphics = ctypes.util.find_library("CoreGraphics")
        else:
            # macOS Big Sur and newer
            coregraphics = "/System/Library/Frameworks/CoreGraphics.framework/Versions/Current/CoreGraphics"

        if not coregraphics:
            msg = "No CoreGraphics library found."
            raise ScreenShotError(msg)
        self.core = ctypes.cdll.LoadLibrary(coregraphics)

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""
        cfactory = self._cfactory
        attrs = {"core": self.core}
        for func, (attr, argtypes, restype) in CFUNCTIONS.items():
            cfactory(attrs[attr], func, argtypes, restype)

    def _set_cconstants(self) -> None:
        """Set all ctypes constants and attach them to attributes."""
        self.constants = {}
        for name, value in CCONSTANTS.items():
            if isinstance(value, type) and hasattr(value, "in_dll"):
                self.constants[name] = value.in_dll(self.core, name)
            else:
                self.constants[name] = value

    def _monitors_impl(self) -> None:
        """Get positions of monitors. It will populate self._monitors."""
        int_ = int
        core = self.core

        # All monitors
        # We need to update the value with every single monitor found
        # using CGRectUnion.  Else we will end with infinite values.
        all_monitors = CGRect()
        self._monitors.append({})

        # Each monitor
        display_count = c_uint32(0)
        active_displays = (c_uint32 * self.max_displays)()
        core.CGGetActiveDisplayList(self.max_displays, active_displays, ctypes.byref(display_count))
        for idx in range(display_count.value):
            display = active_displays[idx]
            rect = core.CGDisplayBounds(display)
            rect = core.CGRectStandardize(rect)
            width, height = rect.size.width, rect.size.height

            # 0.0: normal
            # 90.0: right
            # -90.0: left
            if core.CGDisplayRotation(display) in {90.0, -90.0}:
                width, height = height, width

            self._monitors.append(
                {
                    "left": int_(rect.origin.x),
                    "top": int_(rect.origin.y),
                    "width": int_(width),
                    "height": int_(height),
                },
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

    def _windows_impl(self) -> None:
        core = self.core
        constants = self.constants
        kCGWindowListOptionOnScreenOnly = constants["kCGWindowListOptionOnScreenOnly"]  # noqa: N806
        kCFNumberSInt32Type = constants["kCFNumberSInt32Type"] # noqa: N806
        kCGWindowNumber = constants["kCGWindowNumber"] # noqa: N806
        kCGWindowName = constants["kCGWindowName"] # noqa: N806
        kCGWindowOwnerName = constants["kCGWindowOwnerName"] # noqa: N806
        kCGWindowBounds = constants["kCGWindowBounds"] # noqa: N806
        kCFStringEncodingUTF8 = constants["kCFStringEncodingUTF8"] # noqa: N806

        window_list = core.CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, 0)

        window_count = core.CFArrayGetCount(window_list)

        str_buf = ctypes.create_string_buffer(256)
        self._windows = []
        for i in range(window_count):
            window_info = core.CFArrayGetValueAtIndex(window_list, i)
            window_id = c_int32()
            core.CFNumberGetValue(
                core.CFDictionaryGetValue(window_info, kCGWindowNumber), kCFNumberSInt32Type, ctypes.byref(window_id)
            )

            core.CFStringGetCString(
                core.CFDictionaryGetValue(window_info, kCGWindowName), str_buf, 256, kCFStringEncodingUTF8
            )
            window_name = str_buf.value.decode("utf-8")

            core.CFStringGetCString(
                core.CFDictionaryGetValue(window_info, kCGWindowOwnerName), str_buf, 256, kCFStringEncodingUTF8
            )
            process_name = str_buf.value.decode("utf-8")

            window_bound_ref = core.CFDictionaryGetValue(window_info, kCGWindowBounds)
            window_bounds = CGRect()
            core.CGRectMakeWithDictionaryRepresentation(window_bound_ref, ctypes.byref(window_bounds))

            self._windows.append(
                {
                    "id": window_id.value,
                    "name": window_name,
                    "process": process_name,
                    "bounds": {
                        "left": int(window_bounds.origin.x),
                        "top": int(window_bounds.origin.y),
                        "width": int(window_bounds.size.width),
                        "height": int(window_bounds.size.height),
                    },
                }
            )

    def _image_to_data(self, image_ref: c_void_p, /) -> bytearray:
        """Convert a CGImageRef to a bytearray."""
        core = self.core
        width = core.CGImageGetWidth(image_ref)
        height = core.CGImageGetHeight(image_ref)
        prov = copy_data = None
        try:
            prov = core.CGImageGetDataProvider(image_ref)
            copy_data = core.CGDataProviderCopyData(prov)
            data_ref = core.CFDataGetBytePtr(copy_data)
            buf_len = core.CFDataGetLength(copy_data)
            raw = ctypes.cast(data_ref, POINTER(c_ubyte * buf_len))
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

            return data
        finally:
            if prov:
                core.CGDataProviderRelease(prov)
            if copy_data:
                core.CFRelease(copy_data)

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB."""
        core = self.core
        rect = CGRect((monitor["left"], monitor["top"]), (monitor["width"], monitor["height"]))

        image_ref = core.CGWindowListCreateImage(rect, 1, 0, 0)
        if not image_ref:
            msg = "CoreGraphics.CGWindowListCreateImage() failed."
            raise ScreenShotError(msg)

        width = core.CGImageGetWidth(image_ref)
        height = core.CGImageGetHeight(image_ref)
        data = self._image_to_data(image_ref)

        return self.cls_image(data, monitor, size=Size(width, height))

    def _grab_window_impl(self, window: Window, /) -> ScreenShot:
        """Retrieve all pixels from a window. Pixels have to be RGB."""
        core = self.core
        constants = self.constants
        bounds = window["bounds"]

        rect = constants["CGRectNull"]
        list_option = constants["kCGWindowListOptionIncludingWindow"]
        window_id = window["id"]
        image_option = constants["kCGWindowImageBoundsIgnoreFraming"]

        image_ref = core.CGWindowListCreateImage(rect, list_option, window_id, image_option)

        if not image_ref:
            msg = "CoreGraphics.CGWindowListCreateImage() failed."
            raise ScreenShotError(msg)

        width = core.CGImageGetWidth(image_ref)
        height = core.CGImageGetHeight(image_ref)
        data = self._image_to_data(image_ref)

        return self.cls_image(data, bounds, size=Size(width, height))

    def _cursor_impl(self) -> ScreenShot | None:
        """Retrieve all cursor data. Pixels have to be RGB."""
        return None
