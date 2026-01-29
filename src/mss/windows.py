"""Windows GDI-based backend for MSS.

Uses user32/gdi32 APIs to capture the desktop and enumerate monitors.
This implementation uses CreateDIBSection for direct memory access to pixel data.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import POINTER, WINFUNCTYPE, Structure, WinError, _Pointer
from ctypes.wintypes import (
    BOOL,
    BYTE,
    DWORD,
    HANDLE,
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
CCHDEVICENAME = 32
MONITORINFOF_PRIMARY = 0x01
EDD_GET_DEVICE_INTERFACE_NAME = 0x00000001


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


class MONITORINFOEXW(Structure):
    """Extended monitor information structure.
    https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-monitorinfoexw
    """

    _fields_ = (
        ("cbSize", DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", DWORD),
        ("szDevice", WORD * CCHDEVICENAME),
    )


class DISPLAY_DEVICEW(Structure):  # noqa: N801
    """Display device information structure.
    https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-display_devicew
    """

    _fields_ = (
        ("cb", DWORD),
        ("DeviceName", WORD * 32),
        ("DeviceString", WORD * 128),
        ("StateFlags", DWORD),
        ("DeviceID", WORD * 128),
        ("DeviceKey", WORD * 128),
    )


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
            # Some functions return NULL/0 on failure without setting last error.  (Example: CreateDIBSection
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
    "CreateCompatibleDC": ("gdi32", [HDC], HDC, _errcheck),
    # CreateDIBSection: ppvBits (4th param) receives a pointer to the DIB pixel data.
    # hSection is NULL and offset is 0 to have the system allocate the memory.
    "CreateDIBSection": ("gdi32", [HDC, POINTER(BITMAPINFO), UINT, POINTER(LPVOID), HANDLE, DWORD], HBITMAP, _errcheck),
    "DeleteDC": ("gdi32", [HDC], HDC, _errcheck),
    "DeleteObject": ("gdi32", [HGDIOBJ], BOOL, _errcheck),
    "EnumDisplayDevicesW": ("user32", [POINTER(WORD), DWORD, POINTER(DISPLAY_DEVICEW), DWORD], BOOL, None),
    "EnumDisplayMonitors": ("user32", [HDC, LPCRECT, MONITORNUMPROC, LPARAM], BOOL, _errcheck),
    # GdiFlush flushes the calling thread's current batch of GDI operations.
    # This ensures DIB memory is fully updated before reading.
    "GdiFlush": ("gdi32", [], BOOL, None),
    # While GetSystemMetrics will return 0 if the parameter is invalid, it will also sometimes return 0 if the
    # parameter is valid but the value is actually 0 (e.g., SM_CLEANBOOT on a normal boot).  Thus, we do not attach an
    # errcheck function here.
    "GetSystemMetrics": ("user32", [INT], INT, None),
    "GetMonitorInfoW": ("user32", [HMONITOR, POINTER(MONITORINFOEXW)], BOOL, _errcheck),
    "GetWindowDC": ("user32", [HWND], HDC, _errcheck),
    "ReleaseDC": ("user32", [HWND, HDC], INT, _errcheck),
    # SelectObject returns NULL on error the way we call it.  If it's called to select a region, it returns HGDI_ERROR
    # on error.
    "SelectObject": ("gdi32", [HDC, HGDIOBJ], HGDIOBJ, _errcheck),
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for Microsoft Windows.

    This implementation uses CreateDIBSection for direct memory access to pixel data,
    which eliminates the need for GetDIBits. The DIB pixel data is written directly
    to system-managed memory that we can read from.

    This has no Windows-specific constructor parameters.

    .. seealso::

        :py:class:`mss.base.MSSBase`
            Lists constructor parameters.
    """

    __slots__ = {
        "_bmi",
        "_dib",
        "_dib_array",
        "_dib_bits",
        "_memdc",
        "_region_width_height",
        "_srcdc",
        "gdi32",
        "user32",
    }

    def __init__(self, /, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # user32 and gdi32 should not be changed after initialization.
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        self._set_cfunctions()
        self._set_dpi_awareness()

        # Available instance-specific variables
        self._region_width_height: tuple[int, int] | None = None
        self._dib: HBITMAP | None = None
        self._dib_bits: LPVOID = LPVOID()  # Pointer to DIB pixel data
        self._dib_array: ctypes.Array[ctypes.c_char] | None = None  # Cached array view of DIB memory
        self._srcdc = self.user32.GetWindowDC(0)
        self._memdc = self.gdi32.CreateCompatibleDC(self._srcdc)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        # biWidth and biHeight are set in _grab_impl().
        bmi.bmiHeader.biPlanes = 1  # Always 1
        bmi.bmiHeader.biBitCount = 32  # 32-bit RGBX
        bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
        bmi.bmiHeader.biSizeImage = 0  # Windows infers the size
        bmi.bmiHeader.biXPelsPerMeter = 0  # Unspecified
        bmi.bmiHeader.biYPelsPerMeter = 0  # Unspecified
        bmi.bmiHeader.biClrUsed = 0
        bmi.bmiHeader.biClrImportant = 0
        self._bmi = bmi

    def _close_impl(self) -> None:
        # Clean-up
        if self._dib:
            self.gdi32.DeleteObject(self._dib)
            self._dib = None

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
        def callback(hmonitor: HMONITOR, _data: HDC, rect: LPRECT, _dc: LPARAM) -> bool:
            """Callback for monitorenumproc() function, it will return
            a RECT with appropriate values.
            """
            # Get monitor info to check if it's the primary monitor and get device name
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            user32.GetMonitorInfoW(hmonitor, ctypes.byref(info))

            rct = rect.contents
            left = int_(rct.left)
            top = int_(rct.top)
            # Check the dwFlags field for MONITORINFOF_PRIMARY
            is_primary = bool(info.dwFlags & MONITORINFOF_PRIMARY)
            # Extract device name (null-terminated wide string)
            device_name = ctypes.wstring_at(ctypes.addressof(info.szDevice))

            # Get friendly device string (manufacturer/model info)
            display_device = DISPLAY_DEVICEW()
            display_device.cb = ctypes.sizeof(DISPLAY_DEVICEW)
            device_string = device_name

            # EnumDisplayDevicesW can get more detailed info about the device
            if user32.EnumDisplayDevicesW(
                ctypes.cast(ctypes.addressof(info.szDevice), POINTER(WORD)),
                0,
                ctypes.byref(display_device),
                0,
            ):
                # DeviceString contains the friendly name like "Generic PnP Monitor" or manufacturer name
                device_string = ctypes.wstring_at(ctypes.addressof(display_device.DeviceString))

            self._monitors.append(
                {
                    "left": left,
                    "top": top,
                    "width": int_(rct.right) - left,
                    "height": int_(rct.bottom) - top,
                    "is_primary": is_primary,
                    "name": device_string,
                },
            )
            return True

        user32.EnumDisplayMonitors(0, None, callback, 0)

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor using CreateDIBSection.

        CreateDIBSection creates a DIB with system-managed memory backing,
        allowing BitBlt to write directly to memory we can read. This eliminates
        the need for a separate GetDIBits call.

        Note on biHeight: A bottom-up DIB is specified by setting the height to a
        positive number, while a top-down DIB is specified by setting the height
        to a negative number. We use negative height for top-down orientation.
        https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapinfoheader
        https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection
        """
        srcdc, memdc = self._srcdc, self._memdc
        gdi = self.gdi32
        width, height = monitor["width"], monitor["height"]

        if self._region_width_height != (width, height):
            self._region_width_height = (width, height)
            self._bmi.bmiHeader.biWidth = width
            self._bmi.bmiHeader.biHeight = -height  # Negative for top-down DIB

            if self._dib:
                gdi.DeleteObject(self._dib)
                self._dib = None

            # CreateDIBSection creates the DIB and returns a pointer to the pixel data
            self._dib_bits = LPVOID()
            self._dib = gdi.CreateDIBSection(
                memdc,
                self._bmi,
                DIB_RGB_COLORS,
                ctypes.byref(self._dib_bits),
                None,  # hSection = NULL (system allocates memory)
                0,  # offset = 0
            )
            gdi.SelectObject(memdc, self._dib)

            # Create a ctypes array type that maps directly to the DIB memory.
            # This avoids the overhead of ctypes.string_at() creating an intermediate bytes object.
            size = width * height * 4
            array_type = ctypes.c_char * size
            self._dib_array = ctypes.cast(self._dib_bits, POINTER(array_type)).contents

        # BitBlt copies screen content directly into the DIB's memory
        gdi.BitBlt(memdc, 0, 0, width, height, srcdc, monitor["left"], monitor["top"], SRCCOPY | CAPTUREBLT)

        # Flush GDI operations to ensure DIB memory is fully updated before reading.
        # This ensures the BitBlt has completed before we access the memory.
        gdi.GdiFlush()

        # Read directly from DIB memory via the cached array view
        assert self._dib_array is not None  # noqa: S101  for type checker
        return self.cls_image(bytearray(self._dib_array), monitor)

    def _cursor_impl(self) -> ScreenShot | None:
        """Retrieve all cursor data. Pixels have to be RGB."""
        return None
