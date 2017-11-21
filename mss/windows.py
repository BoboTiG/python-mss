# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from __future__ import division

import ctypes
import ctypes.wintypes

from .base import MSSBase
from .exception import ScreenShotError

__all__ = ('MSS',)


class BITMAPINFOHEADER(ctypes.Structure):
    """ Information about the dimensions and color format of a DIB. """

    _fields_ = [('biSize', ctypes.wintypes.DWORD),
                ('biWidth', ctypes.wintypes.LONG),
                ('biHeight', ctypes.wintypes.LONG),
                ('biPlanes', ctypes.wintypes.WORD),
                ('biBitCount', ctypes.wintypes.WORD),
                ('biCompression', ctypes.wintypes.DWORD),
                ('biSizeImage', ctypes.wintypes.DWORD),
                ('biXPelsPerMeter', ctypes.wintypes.LONG),
                ('biYPelsPerMeter', ctypes.wintypes.LONG),
                ('biClrUsed', ctypes.wintypes.DWORD),
                ('biClrImportant', ctypes.wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    """
    Structure that defines the dimensions and color information for a DIB.
    """

    _fields_ = [('bmiHeader', BITMAPINFOHEADER),
                ('bmiColors', ctypes.wintypes.DWORD * 3)]


class MSS(MSSBase):
    """ Multiple ScreenShots implementation for Microsoft Windows. """

    __scale_factor = None  # type: float

    def __init__(self):
        # type: () -> None
        """ Windows initialisations. """

        self.monitorenumproc = ctypes.WINFUNCTYPE(
            ctypes.wintypes.INT,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD,
            ctypes.POINTER(ctypes.wintypes.RECT),
            ctypes.wintypes.DOUBLE
        )
        set_argtypes(self.monitorenumproc)
        set_restypes()

    @property
    def scale_factor(self):
        """ Compute the scale factor. """

        if not self.__scale_factor:
            display = None
            try:
                display = ctypes.windll.user32.GetWindowDC(0)
                width = ctypes.windll.gdi32.GetDeviceCaps(display, 8)
                width_orig = ctypes.windll.gdi32.GetDeviceCaps(display, 118)
                scale = (100 + 100 - width * 100 // width_orig) / 100
                self.__scale_factor = round(scale * 4) / 4
            finally:
                if display:
                    ctypes.windll.gdi32.DeleteObject(display)

        return self.__scale_factor

    def scale(self, value):
        # type: (float) -> int
        """ Compute a monitor value at scale, rounded to 2. """

        if self.scale_factor == 1.0:
            return int(value)
        return int(value * self.scale_factor * 2 + 0.5) // 2

    @property
    def monitors(self):
        # type: () -> List[Dict[str, int]]
        """ Get positions of monitors (see parent class). """

        if not self._monitors:
            # All monitors
            sm_xvirtualscreen, sm_yvirtualscreen = 76, 77
            sm_cxvirtualscreen, sm_cyvirtualscreen = 78, 79
            left = ctypes.windll.user32.GetSystemMetrics(sm_xvirtualscreen)
            right = ctypes.windll.user32.GetSystemMetrics(sm_cxvirtualscreen)
            top = ctypes.windll.user32.GetSystemMetrics(sm_yvirtualscreen)
            bottom = ctypes.windll.user32.GetSystemMetrics(sm_cyvirtualscreen)
            self._monitors.append({
                'left': self.scale(left),
                'top': self.scale(top),
                'width': self.scale(right - left),
                'height': self.scale(bottom - top),
                'scale': self.scale_factor,
            })

            # Each monitors
            def _callback(monitor, data, rect, dc_):
                # type: (Any, Any, Any, float) -> int
                """
                Callback for monitorenumproc() function, it will return
                a RECT with appropriate values.
                """

                del monitor, data, dc_
                rct = rect.contents
                self._monitors.append({
                    'left': self.scale(rct.left),
                    'top': self.scale(rct.top),
                    'width': self.scale(rct.right - rct.left),
                    'height': self.scale(rct.bottom - rct.top),
                    'scale': self.scale_factor,
                })
                return 1

            callback = self.monitorenumproc(_callback)
            ctypes.windll.user32.EnumDisplayMonitors(0, 0, callback, 0)

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
                'left': monitor[0],
                'top': monitor[1],
                'width': monitor[2] - monitor[0],
                'height': monitor[3] - monitor[1],
            }

        srcdc = memdc = bmp = None
        try:
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = monitor['width']
            bmi.bmiHeader.biHeight = -monitor['height']  # Why minus? See [1]
            bmi.bmiHeader.biPlanes = 1  # Always 1
            bmi.bmiHeader.biBitCount = 32  # See [2]
            bmi.bmiHeader.biCompression = 0  # 0 = BI_RGB (no compression)
            bmi.bmiHeader.biClrUsed = 0  # See [3]
            bmi.bmiHeader.biClrImportant = 0  # See [3]

            buf_len = monitor['width'] * monitor['height'] * 4  # See [2]
            data = ctypes.create_string_buffer(buf_len)
            srcdc = ctypes.windll.user32.GetWindowDC(0)

            memdc = ctypes.windll.gdi32.CreateCompatibleDC(srcdc)
            bmp = ctypes.windll.gdi32.CreateCompatibleBitmap(
                srcdc, monitor['width'], monitor['height'])

            ctypes.windll.gdi32.SelectObject(memdc, bmp)
            ctypes.windll.gdi32.BitBlt(memdc, 0, 0,
                                       monitor['width'], monitor['height'],
                                       srcdc,
                                       monitor['left'], monitor['top'],
                                       0xcc0020)  # SRCCOPY

            bits = ctypes.windll.gdi32.GetDIBits(
                memdc, bmp, 0, monitor['height'], data, bmi, 0)
            if bits != monitor['height']:
                del data
                raise ScreenShotError('gdi32.GetDIBits() failed.', locals())
        finally:
            # Clean up
            if srcdc:
                ctypes.windll.gdi32.DeleteObject(srcdc)
            if memdc:
                ctypes.windll.gdi32.DeleteObject(memdc)
            if bmp:
                ctypes.windll.gdi32.DeleteObject(bmp)

        return self.cls_image(data, monitor)


def set_argtypes(callback):
    # type: (Callable[[int, Any, Any, Any, float], int]) -> None
    """ Functions arguments. """

    ctypes.windll.user32.GetSystemMetrics.argtypes = [ctypes.wintypes.INT]
    ctypes.windll.user32.EnumDisplayMonitors.argtypes = [
        ctypes.wintypes.HDC,
        ctypes.c_void_p,
        callback,
        ctypes.wintypes.LPARAM]
    ctypes.windll.user32.GetWindowDC.argtypes = [ctypes.wintypes.HWND]
    ctypes.windll.gdi32.GetDeviceCaps.argtypes = [ctypes.wintypes.HWND,
                                                  ctypes.wintypes.INT]
    ctypes.windll.gdi32.CreateCompatibleDC.argtypes = [ctypes.wintypes.HDC]
    ctypes.windll.gdi32.CreateCompatibleBitmap.argtypes = [
        ctypes.wintypes.HDC,
        ctypes.wintypes.INT,
        ctypes.wintypes.INT]
    ctypes.windll.gdi32.SelectObject.argtypes = [ctypes.wintypes.HDC,
                                                 ctypes.wintypes.HGDIOBJ]
    ctypes.windll.gdi32.BitBlt.argtypes = [
        ctypes.wintypes.HDC,
        ctypes.wintypes.INT,
        ctypes.wintypes.INT,
        ctypes.wintypes.INT,
        ctypes.wintypes.INT,
        ctypes.wintypes.HDC,
        ctypes.wintypes.INT,
        ctypes.wintypes.INT,
        ctypes.wintypes.DWORD]
    ctypes.windll.gdi32.DeleteObject.argtypes = [ctypes.wintypes.HGDIOBJ]
    ctypes.windll.gdi32.GetDIBits.argtypes = [
        ctypes.wintypes.HDC,
        ctypes.wintypes.HBITMAP,
        ctypes.wintypes.UINT,
        ctypes.wintypes.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        ctypes.wintypes.UINT]


def set_restypes():
    # type: () -> None
    """ Functions return type. """

    ctypes.windll.user32.GetSystemMetrics.restype = ctypes.wintypes.INT
    ctypes.windll.user32.EnumDisplayMonitors.restype = ctypes.wintypes.BOOL
    ctypes.windll.user32.GetWindowDC.restype = ctypes.wintypes.HDC
    ctypes.windll.gdi32.GetDeviceCaps.restype = ctypes.wintypes.INT
    ctypes.windll.gdi32.CreateCompatibleDC.restype = ctypes.wintypes.HDC
    ctypes.windll.gdi32.CreateCompatibleBitmap.restype = \
        ctypes.wintypes.HBITMAP
    ctypes.windll.gdi32.SelectObject.restype = ctypes.wintypes.HGDIOBJ
    ctypes.windll.gdi32.BitBlt.restype = ctypes.wintypes.BOOL
    ctypes.windll.gdi32.GetDIBits.restype = ctypes.wintypes.INT
    ctypes.windll.gdi32.DeleteObject.restype = ctypes.wintypes.BOOL
