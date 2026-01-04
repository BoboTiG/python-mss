"""Windows GDI-based backend for MSS.

Uses user32/gdi32 APIs to capture the desktop and enumerate monitors.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import POINTER, WINFUNCTYPE, Structure, WinError, _Pointer
from ctypes.wintypes import (
    BOOL,
    BYTE,
    DWORD,
    HBITMAP,
    HDC,
    HGDIOBJ,
    HMONITOR,
    HWND,
    INT,
    LONG,
    LPARAM,
    LPRECT,
    LPVOID,
    RECT,
    UINT,
    WORD,
)
from typing import TYPE_CHECKING, Any, Callable

from mss.base import MSSBase
from mss.exception import ScreenShotError

if TYPE_CHECKING:  # pragma: nocover
    from mss.models import CFunctionsErrChecked, Monitor
    from mss.screenshot import ScreenShot

__all__ = ("MSS",)

BACKENDS = ["default"]


LPCRECT = POINTER(RECT)  # Actually a const pointer, but ctypes has no const.
CAPTUREBLT = 0x40000000
DIB_RGB_COLORS = 0
SRCCOPY = 0x00CC0020


class BITMAPINFOHEADER(Structure):
    """Information about the dimensions and color format of a DIB."""

    _fields_ = (
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
    )


class BITMAPINFO(Structure):
    """Structure that defines the dimensions and color information for a DIB."""

    # The bmiColors entry is variable length, but it's unused the way we do things.  We declare it to be four bytes,
    # which is how it's declared in C.
    _fields_ = (("bmiHeader", BITMAPINFOHEADER), ("bmiColors", BYTE * 4))


MONITORNUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)


def _errcheck(result: BOOL | _Pointer, func: Callable, arguments: tuple) -> tuple:
    """If the result is zero, raise an exception."""
    if not result:
        # Notably, the errno that is in winerror may not be relevant.  Use the winerror and strerror attributes
        # instead.
        winerror = WinError()
        details = {
            "func": func.__name__,
            "args": arguments,
            "error_code": winerror.winerror,
            "error_msg": winerror.strerror,
        }
        if winerror.winerror == 0:
            # Some functions return NULL/0 on failure without setting last error.  (Example: CreateCompatibleBitmap
            # with an invalid HDC.)
            msg = f"Windows graphics function failed (no error provided): {func.__name__}"
            raise ScreenShotError(msg, details=details)
        msg = f"Windows graphics function failed: {func.__name__}: {winerror.strerror}"
        raise ScreenShotError(msg, details=details) from winerror
    return arguments


# C functions that will be initialised later.
#
# Available attr: gdi32, user32.
#
# Note: keep it sorted by cfunction.
CFUNCTIONS: CFunctionsErrChecked = {
    # Syntax: cfunction: (attr, argtypes, restype, errcheck)
    "BitBlt": ("gdi32", [HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD], BOOL, _errcheck),
    "CreateCompatibleBitmap": ("gdi32", [HDC, INT, INT], HBITMAP, _errcheck),
    "CreateCompatibleDC": ("gdi32", [HDC], HDC, _errcheck),
    "DeleteDC": ("gdi32", [HDC], HDC, _errcheck),
    "DeleteObject": ("gdi32", [HGDIOBJ], BOOL, _errcheck),
    "EnumDisplayMonitors": ("user32", [HDC, LPCRECT, MONITORNUMPROC, LPARAM], BOOL, _errcheck),
    "GetDIBits": ("gdi32", [HDC, HBITMAP, UINT, UINT, LPVOID, POINTER(BITMAPINFO), UINT], INT, _errcheck),
    # While GetSystemMetrics will return 0 if the parameter is invalid, it will also sometimes return 0 if the
    # parameter is valid but the value is actually 0 (e.g., SM_CLEANBOOT on a normal boot).  Thus, we do not attach an
    # errcheck function here.
    "GetSystemMetrics": ("user32", [INT], INT, None),
    "GetWindowDC": ("user32", [HWND], HDC, _errcheck),
    "ReleaseDC": ("user32", [HWND, HDC], INT, _errcheck),
    # SelectObject returns NULL on error the way we call it.  If it's called to select a region, it returns HGDI_ERROR
    # on error.
    "SelectObject": ("gdi32", [HDC, HGDIOBJ], HGDIOBJ, _errcheck),
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for Microsoft Windows.

    This has no Windows-specific constructor parameters.

    .. seealso::

        :py:class:`mss.base.MSSBase`
            Lists constructor parameters.
    """

    __slots__ = {"_bmi", "_bmp", "_data", "_memdc", "_region_width_height", "_srcdc", "gdi32", "user32"}

    def __init__(self, /, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._set_cfunctions()
        self._set_dpi_awareness()

        # Available instance-specific variables
        self._region_width_height: tuple[int, int] | None = None
        self._bmp: HBITMAP | None = None
        self._srcdc = self.user32.GetWindowDC(0)
        self._memdc = self.gdi32.CreateCompatibleDC(self._srcdc)
        self._data: ctypes.Array[ctypes.c_char] | None = None

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        # biWidth and biHeight are set in _grab_impl().
        bmi.bmiHeader.biPlanes = 1  # Always 1
        bmi.bmiHeader.biBitCount = 32  # See grab.__doc__ [2]
        bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
        bmi.bmiHeader.biSizeImage = 0  # Windows infers the size
        bmi.bmiHeader.biXPelsPerMeter = 0  # Unspecified
        bmi.bmiHeader.biYPelsPerMeter = 0  # Unspecified
        bmi.bmiHeader.biClrUsed = 0  # See grab.__doc__ [3]
        bmi.bmiHeader.biClrImportant = 0  # See grab.__doc__ [3]
        self._bmi = bmi

    def _close_impl(self) -> None:
        # Clean-up
        if self._bmp:
            self.gdi32.DeleteObject(self._bmp)
            self._bmp = None

        if self._memdc:
            self.gdi32.DeleteDC(self._memdc)
            self._memdc = None

        if self._srcdc:
            self.user32.ReleaseDC(0, self._srcdc)
            self._srcdc = None

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""
        cfactory = self._cfactory
        attrs = {
            "gdi32": self.gdi32,
            "user32": self.user32,
        }
        for func, (attr, argtypes, restype, errcheck) in CFUNCTIONS.items():
            cfactory(attrs[attr], func, argtypes, restype, errcheck)

    def _set_dpi_awareness(self) -> None:
        """Set DPI awareness to capture full screen on Hi-DPI monitors."""
        version = sys.getwindowsversion()[:2]
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
            },
        )

        # Each monitor
        @MONITORNUMPROC
        def callback(_monitor: HMONITOR, _data: HDC, rect: LPRECT, _dc: LPARAM) -> bool:
            """Callback for monitorenumproc() function, it will return
            a RECT with appropriate values.
            """
            rct = rect.contents
            self._monitors.append(
                {
                    "left": int_(rct.left),
                    "top": int_(rct.top),
                    "width": int_(rct.right) - int_(rct.left),
                    "height": int_(rct.bottom) - int_(rct.top),
                },
            )
            return True

        user32.EnumDisplayMonitors(0, None, callback, 0)

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB.

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
        srcdc, memdc = self._srcdc, self._memdc
        gdi = self.gdi32
        width, height = monitor["width"], monitor["height"]

        if self._region_width_height != (width, height):
            self._region_width_height = (width, height)
            self._bmi.bmiHeader.biWidth = width
            self._bmi.bmiHeader.biHeight = -height  # Why minus? See [1]
            self._data = ctypes.create_string_buffer(width * height * 4)  # [2]
            if self._bmp:
                gdi.DeleteObject(self._bmp)
                # Set to None to prevent another DeleteObject in case CreateCompatibleBitmap raises an exception.
                self._bmp = None
            self._bmp = gdi.CreateCompatibleBitmap(srcdc, width, height)
            gdi.SelectObject(memdc, self._bmp)

        gdi.BitBlt(memdc, 0, 0, width, height, srcdc, monitor["left"], monitor["top"], SRCCOPY | CAPTUREBLT)
        assert self._data is not None  # noqa: S101 for type checker
        scanlines_copied = gdi.GetDIBits(memdc, self._bmp, 0, height, self._data, self._bmi, DIB_RGB_COLORS)
        if scanlines_copied != height:
            # If the result was 0 (failure), an exception would have been raised by _errcheck.  This is just a sanity
            # clause.
            msg = f"gdi32.GetDIBits() failed: only {scanlines_copied} scanlines copied instead of {height}"
            raise ScreenShotError(msg)

        return self.cls_image(bytearray(self._data), monitor)

    def _cursor_impl(self) -> ScreenShot | None:
        """Retrieve all cursor data. Pixels have to be RGB."""
        return None
