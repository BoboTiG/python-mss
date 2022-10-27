"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import ctypes
import sys
import threading
from ctypes import POINTER, WINFUNCTYPE, Structure, c_void_p
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
)
from typing import Any, Dict

from .base import MSSBase
from .exception import ScreenShotError
from .models import CFunctions, Monitor
from .screenshot import ScreenShot

__all__ = ("MSS",)


CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


class BITMAPINFOHEADER(Structure):
    """Information about the dimensions and color format of a DIB."""

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
        ("biClrImportant", DWORD),
    ]


class BITMAPINFO(Structure):
    """
    Structure that defines the dimensions and color information for a DIB.
    """

    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


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
    "DeleteObject": ("gdi32", [HGDIOBJ], INT),
    "EnumDisplayMonitors": ("user32", [HDC, c_void_p, MONITORNUMPROC, LPARAM], BOOL),
    "GetDeviceCaps": ("gdi32", [HWND, INT], INT),
    "GetDIBits": (
        "gdi32",
        [HDC, HBITMAP, UINT, UINT, c_void_p, POINTER(BITMAPINFO), UINT],
        BOOL,
    ),
    "GetSystemMetrics": ("user32", [INT], INT),
    "GetWindowDC": ("user32", [HWND], HDC),
    "SelectObject": ("gdi32", [HDC, HGDIOBJ], HGDIOBJ),
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for Microsoft Windows."""

    __slots__ = {"_bbox", "_bmi", "_data", "gdi32", "user32"}

    # Class attributes instanced one time to prevent resource leaks.
    bmp = None
    memdc = None

    # A dict to maintain *srcdc* values created by multiple threads.
    _srcdc_dict: Dict[threading.Thread, int] = {}

    def __init__(self, **_: Any) -> None:
        """Windows initialisations."""

        super().__init__()

        self.user32 = ctypes.WinDLL("user32")
        self.gdi32 = ctypes.WinDLL("gdi32")
        self._set_cfunctions()
        self._set_dpi_awareness()

        self._bbox = {"height": 0, "width": 0}
        self._data: ctypes.Array[ctypes.c_char] = ctypes.create_string_buffer(0)

        srcdc = self._get_srcdc()
        if not MSS.memdc:
            MSS.memdc = self.gdi32.CreateCompatibleDC(srcdc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biPlanes = 1  # Always 1
        bmi.bmiHeader.biBitCount = 32  # See grab.__doc__ [2]
        bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
        bmi.bmiHeader.biClrUsed = 0  # See grab.__doc__ [3]
        bmi.bmiHeader.biClrImportant = 0  # See grab.__doc__ [3]
        self._bmi = bmi

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""

        cfactory = self._cfactory
        attrs = {
            "gdi32": self.gdi32,
            "user32": self.user32,
        }
        for func, (attr, argtypes, restype) in CFUNCTIONS.items():
            cfactory(
                attr=attrs[attr],
                func=func,
                argtypes=argtypes,
                restype=restype,
            )

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
            # Windows Vista, 7, 8 and Server 2012
            self.user32.SetProcessDPIAware()

    def _get_srcdc(self) -> int:
        """
        Retrieve a thread-safe HDC from GetWindowDC().
        In multithreading, if the thread that creates *srcdc* is dead, *srcdc* will
        no longer be valid to grab the screen. The *srcdc* attribute is replaced
        with *_srcdc_dict* to maintain the *srcdc* values in multithreading.
        Since the current thread and main thread are always alive, reuse their *srcdc* value first.
        """
        cur_thread, main_thread = threading.current_thread(), threading.main_thread()
        current_srcdc = MSS._srcdc_dict.get(cur_thread) or MSS._srcdc_dict.get(
            main_thread
        )
        if current_srcdc:
            srcdc = current_srcdc
        else:
            srcdc = self.user32.GetWindowDC(0)
            MSS._srcdc_dict[cur_thread] = srcdc
        return srcdc

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

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
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

        srcdc, memdc = self._get_srcdc(), MSS.memdc
        width, height = monitor["width"], monitor["height"]

        if (self._bbox["height"], self._bbox["width"]) != (height, width):
            self._bbox = monitor
            self._bmi.bmiHeader.biWidth = width
            self._bmi.bmiHeader.biHeight = -height  # Why minus? [1]
            self._data = ctypes.create_string_buffer(width * height * 4)  # [2]
            if MSS.bmp:
                self.gdi32.DeleteObject(MSS.bmp)
            MSS.bmp = self.gdi32.CreateCompatibleBitmap(srcdc, width, height)
            self.gdi32.SelectObject(memdc, MSS.bmp)

        self.gdi32.BitBlt(
            memdc,
            0,
            0,
            width,
            height,
            srcdc,
            monitor["left"],
            monitor["top"],
            SRCCOPY | CAPTUREBLT,
        )
        bits = self.gdi32.GetDIBits(
            memdc, MSS.bmp, 0, height, self._data, self._bmi, DIB_RGB_COLORS
        )
        if bits != height:
            raise ScreenShotError("gdi32.GetDIBits() failed.")

        return self.cls_image(bytearray(self._data), monitor)
