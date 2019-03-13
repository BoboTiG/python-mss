# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from __future__ import division

import sys
import ctypes
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
    RECT,
    UINT,
    WORD,
)

from .base import MSSMixin
from .exception import ScreenShotError

__all__ = ("MSS",)


CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


class BITMAPINFOHEADER(ctypes.Structure):
    """ Information about the dimensions and color format of a DIB. """

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


class BITMAPINFO(ctypes.Structure):
    """
    Structure that defines the dimensions and color information for a DIB.
    """

    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", DWORD * 3)]


class MSS(MSSMixin):
    """ Multiple ScreenShots implementation for Microsoft Windows. """

    def __init__(self):
        # type: () -> None
        """ Windows initialisations. """

        self._monitors = []  # type: List[Dict[str, int]]

        self._bbox = {"height": 0, "width": 0}
        self._bmp = None
        self._data = None

        self.monitorenumproc = ctypes.WINFUNCTYPE(
            INT, DWORD, DWORD, ctypes.POINTER(RECT), DOUBLE
        )

        self.user32 = ctypes.WinDLL("user32")
        self.gdi32 = ctypes.WinDLL("gdi32")
        self._set_cfunctions()
        self._set_dpi_awareness()

        self._srcdc = self.user32.GetWindowDC(0)
        self._memdc = self.gdi32.CreateCompatibleDC(self._srcdc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biPlanes = 1  # Always 1
        bmi.bmiHeader.biBitCount = 32  # See grab.__doc__ [2]
        bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
        bmi.bmiHeader.biClrUsed = 0  # See grab.__doc__ [3]
        bmi.bmiHeader.biClrImportant = 0  # See grab.__doc__ [3]
        self._bmi = bmi

    def _set_cfunctions(self):
        """ Set all ctypes functions and attach them to attributes. """

        void = ctypes.c_void_p
        pointer = ctypes.POINTER

        self._cfactory(
            attr=self.user32, func="GetSystemMetrics", argtypes=[INT], restype=INT
        )
        self._cfactory(
            attr=self.user32,
            func="EnumDisplayMonitors",
            argtypes=[HDC, void, self.monitorenumproc, LPARAM],
            restype=BOOL,
        )
        self._cfactory(
            attr=self.user32, func="GetWindowDC", argtypes=[HWND], restype=HDC
        )
        self._cfactory(
            attr=self.user32, func="ReleaseDC", argtypes=[HWND, HGDIOBJ], restype=INT
        )

        self._cfactory(
            attr=self.gdi32, func="GetDeviceCaps", argtypes=[HWND, INT], restype=INT
        )
        self._cfactory(
            attr=self.gdi32, func="CreateCompatibleDC", argtypes=[HDC], restype=HDC
        )
        self._cfactory(attr=self.gdi32, func="DeleteDC", argtypes=[HDC], restype=BOOL)
        self._cfactory(
            attr=self.gdi32,
            func="CreateCompatibleBitmap",
            argtypes=[HDC, INT, INT],
            restype=HBITMAP,
        )
        self._cfactory(
            attr=self.gdi32,
            func="SelectObject",
            argtypes=[HDC, HGDIOBJ],
            restype=HGDIOBJ,
        )
        self._cfactory(
            attr=self.gdi32,
            func="BitBlt",
            argtypes=[HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD],
            restype=BOOL,
        )
        self._cfactory(
            attr=self.gdi32, func="DeleteObject", argtypes=[HGDIOBJ], restype=INT
        )
        self._cfactory(
            attr=self.gdi32,
            func="GetDIBits",
            argtypes=[HDC, HBITMAP, UINT, UINT, void, pointer(BITMAPINFO), UINT],
            restype=BOOL,
        )

    def close(self):
        # type: () -> None
        """ Close GDI handles and free DCs. """

        try:
            self.gdi32.DeleteObject(self._bmp)
            del self._bmp
        except AttributeError:
            pass

        try:
            self.gdi32.DeleteDC(self._memdc)
            del self._memdc
        except (OSError, AttributeError):
            pass

        try:
            self.user32.ReleaseDC(0, self._srcdc)
            del self._srcdc
        except AttributeError:
            pass

    def _set_dpi_awareness(self):
        """ Set DPI aware to capture full screen on Hi-DPI monitors. """

        version = sys.getwindowsversion()[:2]
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

    @property
    def monitors(self):
        # type: () -> List[Dict[str, int]]
        """ Get positions of monitors (see parent class). """

        if not self._monitors:
            # All monitors
            sm_xvirtualscreen, sm_yvirtualscreen = 76, 77
            sm_cxvirtualscreen, sm_cyvirtualscreen = 78, 79
            self._monitors.append(
                {
                    "left": int(self.user32.GetSystemMetrics(sm_xvirtualscreen)),
                    "top": int(self.user32.GetSystemMetrics(sm_yvirtualscreen)),
                    "width": int(self.user32.GetSystemMetrics(sm_cxvirtualscreen)),
                    "height": int(self.user32.GetSystemMetrics(sm_cyvirtualscreen)),
                }
            )

            # Each monitors
            def _callback(monitor, data, rect, dc_):
                # type: (Any, Any, Any, float) -> int
                """
                Callback for monitorenumproc() function, it will return
                a RECT with appropriate values.
                """

                del monitor, data, dc_
                rct = rect.contents
                self._monitors.append(
                    {
                        "left": int(rct.left),
                        "top": int(rct.top),
                        "width": int(rct.right - rct.left),
                        "height": int(rct.bottom - rct.top),
                    }
                )
                return 1

            callback = self.monitorenumproc(_callback)
            self.user32.EnumDisplayMonitors(0, 0, callback, 0)

        return self._monitors

    def grab(self, monitor):
        # type: (Dict[str, int]) -> ScreenShot
        """ Retrieve all pixels from a monitor. Pixels have to be RGB.

            In the code, there are few interesting things:

            [1] bmi.bmiHeader.biHeight = -height

            A bottom-up DIB is specified by setting the height to a
            positive number, while a top-down DIB is specified by
            setting the height to a negative number.
            https://msdn.microsoft.com/en-us/library/ms787796.aspx
            https://msdn.microsoft.com/en-us/library/dd144879%28v=vs.85%29.aspx


            [2] bmi.bmiHeader.biBitCount = 32
                image_data = create_string_buffer(height * width * 4)

            We grab the image in RGBX mode, so that each word is 32bit
            and we have no striding, then we transform to RGB.
            Inspired by https://github.com/zoofIO/flexx


            [3] bmi.bmiHeader.biClrUsed = 0
                bmi.bmiHeader.biClrImportant = 0

            When biClrUsed and biClrImportant are set to zero, there
            is "no" color table, so we can read the pixels of the bitmap
            retrieved by gdi32.GetDIBits() as a sequence of RGB values.
            Thanks to http://stackoverflow.com/a/3688682
        """

        # Convert PIL bbox style
        if isinstance(monitor, tuple):
            monitor = {
                "left": monitor[0],
                "top": monitor[1],
                "width": monitor[2] - monitor[0],
                "height": monitor[3] - monitor[1],
            }

        width, height = monitor["width"], monitor["height"]

        if (self._bbox["height"], self._bbox["width"]) != (height, width):
            self._bbox = monitor
            self._bmi.bmiHeader.biWidth = width
            self._bmi.bmiHeader.biHeight = -height  # Why minus? [1]
            self._data = ctypes.create_string_buffer(width * height * 4)  # [2]
            self._bmp = self.gdi32.CreateCompatibleBitmap(self._srcdc, width, height)
            self.gdi32.SelectObject(self._memdc, self._bmp)

        self.gdi32.BitBlt(
            self._memdc,
            0,
            0,
            width,
            height,
            self._srcdc,
            monitor["left"],
            monitor["top"],
            SRCCOPY | CAPTUREBLT,
        )
        bits = self.gdi32.GetDIBits(
            self._memdc, self._bmp, 0, height, self._data, self._bmi, DIB_RGB_COLORS
        )
        if bits != height:
            raise ScreenShotError("gdi32.GetDIBits() failed.")

        return self.cls_image(self._data, monitor)
