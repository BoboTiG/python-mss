"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import ctypes
import sys
from ctypes import POINTER, WINFUNCTYPE, Structure, c_int, c_void_p
from ctypes.wintypes import (
    BOOL,
    DOUBLE,
    DWORD,
    HBITMAP,
    HDC,
    HGDIOBJ,
    HWND,
    INT,
    LONG,
    LPARAM,
    LPRECT,
    RECT,
    UINT,
    WORD,
    POINT,
    HICON
)
from threading import local
from typing import Any, Optional

from .base import MSSBase
from .exception import ScreenShotError
from .models import CFunctions, Monitor
from .screenshot import ScreenShot

__all__ = ("MSS",)


CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


class BITMAPINFOHEADER(Structure):
    """
    Information about the dimensions and color format of a DIB.
    """

    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD)
    ]


class BITMAPINFO(Structure):
    """
    Structure that defines the dimensions and color information for a DIB.
    """

    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


class CURSORINFO(Structure):
    """
    Information about the cursor.
    """

    _fields_ = [
        ("cbSize", DWORD),
        ("flags", DWORD),
        ("hCursor", HDC),
        ("ptScreenPos", POINT)
    ]


class ICONINFO(Structure):
    """
    Information about an icon or cursor.
    """

    _fields_ = [
        ("fIcon", BOOL),
        ("xHotspot", DWORD),
        ("yHotspot", DWORD),
        ("hbmMask", HBITMAP),
        ("hbmColor", HBITMAP)
    ]


MONITORNUMPROC = WINFUNCTYPE(INT, DWORD, DWORD, POINTER(RECT), DOUBLE)


# C functions that will be initialised later.
#
# This is a dict:
#    cfunction: (attr, argtypes, restype)
#
# Available attr: gdi32, user32.
#
# Note: keep it sorted by cfunction.
CFUNCTIONS: CFunctions = {
    "BitBlt": ("gdi32", [HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD], BOOL),
    "CreateCompatibleBitmap": ("gdi32", [HDC, INT, INT], HBITMAP),
    "CreateCompatibleDC": ("gdi32", [HDC], HDC),
    "DeleteDC": ("gdi32", [HDC], HDC),
    "DeleteObject": ("gdi32", [HGDIOBJ], INT),
    "DrawIcon": ("user32", [HDC, INT, INT, HICON], BOOL),
    "EnumDisplayMonitors": ("user32", [HDC, c_void_p, MONITORNUMPROC, LPARAM], BOOL),
    "GetCursorInfo": ("user32", [POINTER(CURSORINFO)], BOOL),
    "GetDeviceCaps": ("gdi32", [HWND, INT], INT),
    "GetDIBits": ("gdi32", [HDC, HBITMAP, UINT, UINT, c_void_p, POINTER(BITMAPINFO), UINT], BOOL),
    "GetIconInfo": ("user32", [HICON, POINTER(ICONINFO)], BOOL),
    "GetSystemMetrics": ("user32", [INT], INT),
    "GetWindowDC": ("user32", [HWND], HDC),
    "ReleaseDC": ("user32", [HWND, HDC], c_int),
    "SelectObject": ("gdi32", [HDC, HGDIOBJ], HGDIOBJ),
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for Microsoft Windows."""

    __slots__ = {"gdi32", "user32", "_handles"}

    def __init__(self, /, **kwargs: Any) -> None:
        """Windows initialisations."""

        super().__init__(**kwargs)

        self.user32 = ctypes.WinDLL("user32")
        self.gdi32 = ctypes.WinDLL("gdi32")
        self._set_cfunctions()
        self._set_dpi_awareness()

        # Available thread-specific variables
        self._handles = local()
        self._handles.region_width_height = (0, 0)
        self._handles.bmp = None
        self._handles.srcdc = self.user32.GetWindowDC(0)
        self._handles.memdc = self.gdi32.CreateCompatibleDC(self._handles.srcdc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biPlanes = 1  # Always 1
        bmi.bmiHeader.biBitCount = 32  # See grab.__doc__ [2]
        bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
        bmi.bmiHeader.biClrUsed = 0  # See grab.__doc__ [3]
        bmi.bmiHeader.biClrImportant = 0  # See grab.__doc__ [3]
        self._handles.bmi = bmi

        ci = CURSORINFO()
        ci.cbSize = ctypes.sizeof(CURSORINFO)
        self._handles.ci = ci

        iconinfo = ICONINFO()  # 'ii' felt uncomfortable
        self._handles.iconinfo = iconinfo

    def close(self) -> None:
        # Clean-up
        if self._handles.bmp:
            self.gdi32.DeleteObject(self._handles.bmp)
            self._handles.bmp = None

        if self._handles.memdc:
            self.gdi32.DeleteDC(self._handles.memdc)
            self._handles.memdc = None

        if self._handles.srcdc:
            self.user32.ReleaseDC(0, self._handles.srcdc)
            self._handles.srcdc = None

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""

        cfactory = self._cfactory
        attrs = {
            "gdi32": self.gdi32,
            "user32": self.user32,
        }
        for func, (attr, argtypes, restype) in CFUNCTIONS.items():
            cfactory(attrs[attr], func, argtypes, restype)

    def _set_dpi_awareness(self) -> None:
        """Set DPI awareness to capture full screen on Hi-DPI monitors."""

        version = sys.getwindowsversion()[:2]  # pylint: disable=no-member
        if version >= (6, 3):
            # Windows 8.1+
            # Here 2 = PROCESS_PER_MONITOR_DPI_AWARE, which means:
            #     per monitor DPI aware. This app checks for the DPI when it is
            #     created and adjusts the scale factor whenever the DPI changes.
            #     These applications are not automatically scaled by the system.
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        elif (6, 0) <= version < (6, 3):
            # Windows Vista, 7, 8, and Server 2012
            self.user32.SetProcessDPIAware()

    def _monitors_impl(self) -> None:
        """Get positions of monitors. It will populate self._monitors."""

        int_ = int
        user32 = self.user32
        get_system_metrics = user32.GetSystemMetrics

        # All monitors
        self._monitors.append(
            {
                "left": int_(get_system_metrics(76)),  # SM_XVIRTUALSCREEN
                "top": int_(get_system_metrics(77)),  # SM_YVIRTUALSCREEN
                "width": int_(get_system_metrics(78)),  # SM_CXVIRTUALSCREEN
                "height": int_(get_system_metrics(79)),  # SM_CYVIRTUALSCREEN
            }
        )

        # Each monitor
        def _callback(monitor: int, data: HDC, rect: LPRECT, dc_: LPARAM) -> int:
            """
            Callback for monitorenumproc() function, it will return
            a RECT with appropriate values.
            """
            # pylint: disable=unused-argument

            rct = rect.contents
            self._monitors.append(
                {
                    "left": int_(rct.left),
                    "top": int_(rct.top),
                    "width": int_(rct.right) - int_(rct.left),
                    "height": int_(rct.bottom) - int_(rct.top),
                }
            )
            return 1

        callback = MONITORNUMPROC(_callback)
        user32.EnumDisplayMonitors(0, 0, callback, 0)

    def _grab_impl(self, monitor: Monitor, /) -> Optional[ScreenShot]:
        """
        Retrieve all pixels from a monitor. Pixels have to be RGB.

        In the code, there are a few interesting things:

        [1] bmi.bmiHeader.biHeight = -height

        A bottom-up DIB is specified by setting the height to a
        positive number, while a top-down DIB is specified by
        setting the height to a negative number.
        https://msdn.microsoft.com/en-us/library/ms787796.aspx
        https://msdn.microsoft.com/en-us/library/dd144879%28v=vs.85%29.aspx


        [2] bmi.bmiHeader.biBitCount = 32
            image_data = create_string_buffer(height * width * 4)

        We grab the image in RGBX mode, so that each word is 32bit
        and we have no striding.
        Inspired by https://github.com/zoofIO/flexx


        [3] bmi.bmiHeader.biClrUsed = 0
            bmi.bmiHeader.biClrImportant = 0

        When biClrUsed and biClrImportant are set to zero, there
        is "no" color table, so we can read the pixels of the bitmap
        retrieved by gdi32.GetDIBits() as a sequence of RGB values.
        Thanks to http://stackoverflow.com/a/3688682
        """

        srcdc, memdc = self._handles.srcdc, self._handles.memdc
        gdi = self.gdi32
        width, height = monitor["width"], monitor["height"]

        if self._handles.region_width_height != (width, height):
            self._handles.region_width_height = (width, height)
            self._handles.bmi.bmiHeader.biWidth = width
            self._handles.bmi.bmiHeader.biHeight = -height  # Why minus? [1]
            self._handles.data = ctypes.create_string_buffer(width * height * 4)  # [2]
            if self._handles.bmp:
                gdi.DeleteObject(self._handles.bmp)
            self._handles.bmp = gdi.CreateCompatibleBitmap(srcdc, width, height)
            gdi.SelectObject(memdc, self._handles.bmp)

        gdi.BitBlt(memdc, 0, 0, width, height, srcdc, monitor["left"], monitor["top"], SRCCOPY | CAPTUREBLT)
        bits = gdi.GetDIBits(memdc, self._handles.bmp, 0, height, self._handles.data, self._handles.bmi, DIB_RGB_COLORS)
        if bits != height:
            raise ScreenShotError("gdi32.GetDIBits() failed.")

        return self.cls_image(bytearray(self._handles.data), monitor)

    def _cursor_impl(self) -> ScreenShot:
        """Retrieve all cursor data. Pixels have to be RGB.

        [1] user32.DrawIcon(HDC(memdc), 0, 0, hcursor)
        Sometimes the memdc value is greater than the 32 bit limit
        and that results in
        'ctypes.ArgumentError: argument 1: OverflowError: int too long to convert'
        but casting it to HDC type seems to fix the issue.

        [2] user32.GetIconInfo(hcursor, self._handles.iconinfo)
        GetIconInfo also returns the handle for mask bitmap and the handle for color bitmap
        but the color bitmap handle is null in case of monochrome cursors.

        [3] is_monochrome = self._handles.iconinfo.hbmColor is None
        The correct way to detect monochrome cursors seems to be a unique property of their
        mask bitmap. The height of the mask bitmap of a monochrome cursor is twice its width
        (https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-iconinfo)
        But I cannot find the correct way of getting a bitmap's dimensions, therefore I
        just eneded up checking if the color bitmap is null.

        [4]
        The data received using DrawIcon is in the format BGRA but in case of monochrome
        cursors the alpha value of every pixel is 0 for some reason. Therefore, the alpha
        value of every non black pixel has to be manually set to 255.
        """
        srcdc, memdc = self._handles.srcdc, self._handles.memdc
        gdi, user32 = self.gdi32, self.user32
        width, height = 32, 32
        user32.GetCursorInfo(self._handles.ci)
        hcursor = self._handles.ci.hCursor
        pos_screen = self._handles.ci.ptScreenPos

        if self._handles.region_width_height != (width, height):
            self._handles.region_width_height = (width, height)
            self._handles.bmi.bmiHeader.biWidth = width
            self._handles.bmi.bmiHeader.biHeight = -height
            self._handles.data = ctypes.create_string_buffer(width * height * 4)
            if self._handles.bmp:
                gdi.DeleteObject(self._handles.bmp)
            self._handles.bmp = gdi.CreateCompatibleBitmap(srcdc, width, height)
            gdi.SelectObject(memdc, self._handles.bmp)

        user32.DrawIcon(HDC(memdc), 0, 0, hcursor)  # Why HDC? [1]
        bits = gdi.GetDIBits(memdc, self._handles.bmp, 0, height, self._handles.data, self._handles.bmi, DIB_RGB_COLORS)
        if bits != height:
            raise ScreenShotError("gdi32.GetDIBits() failed.")

        user32.GetIconInfo(hcursor, self._handles.iconinfo)  # [2]
        is_monochrome = self._handles.iconinfo.hbmColor is None  # [3]
        ratio = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
        region = {
            "left": round(pos_screen.x * ratio - self._handles.iconinfo.xHotspot),
            "top": round(pos_screen.y * ratio - self._handles.iconinfo.yHotspot),
            "width": 32,
            "height": 32
        }
        data = bytearray(self._handles.data)
        if is_monochrome:
            for i in range(3, len(data), 4):  # [4]
                if data[i-3:i] == b"\x00\x00\x00":
                    data[i] = 0
                else:
                    data[i] = 255
        return self.cls_image(data, region)
