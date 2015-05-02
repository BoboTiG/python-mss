#!/usr/bin/env python
# coding: utf-8
''' A very fast cross-platform multiple screenshots module in pure python
    using ctypes.

    This module is maintained by Mickaël Schoentgen <mickael@jmsinfo.co>.

    Note: please keep this module compatible to Python 2.6.

    You can always get the latest version of this module at:
        https://raw.github.com/BoboTiG/python-mss/master/mss.py
    If that URL should fail, try contacting the author.
'''

from __future__ import division, print_function, unicode_literals

__version__ = '1.0.0'
__author__ = "Mickaël 'Tiger-222' Schoentgen"
__copyright__ = '''
    Copyright (c) 2013-2015, Mickaël 'Tiger-222' Schoentgen

    Permission to use, copy, modify, and distribute this software and its
    documentation for any purpose and without fee or royalty is hereby
    granted, provided that the above copyright notice appear in all copies
    and that both that copyright notice and this permission notice appear
    in supporting documentation or portions thereof, including
    modifications, that you make.
'''
__all__ = ['mss', 'ScreenshotError']

from platform import system
from struct import pack
from zlib import compress, crc32
import sys


class ScreenshotError(Exception):
    ''' Error handling class. '''
    pass


if system() == 'Darwin':
    from Quartz import *
    from LaunchServices import kUTTypePNG
elif system() == 'Linux':
    from os import environ
    from ctypes.util import find_library
    from ctypes import byref, cast, cdll, POINTER, Structure, c_char_p,\
        c_int, c_int32, c_long, c_uint, c_uint32, c_ulong, c_ushort, c_void_p, \
        create_string_buffer

    class Display(Structure):
        pass

    class XWindowAttributes(Structure):
        _fields_ = [('x', c_int32), ('y', c_int32), ('width', c_int32),
                    ('height', c_int32), ('border_width', c_int32),
                    ('depth', c_int32), ('visual', c_ulong), ('root', c_ulong),
                    ('class', c_int32), ('bit_gravity', c_int32),
                    ('win_gravity', c_int32), ('backing_store', c_int32),
                    ('backing_planes', c_ulong), ('backing_pixel', c_ulong),
                    ('save_under', c_int32), ('colourmap', c_ulong),
                    ('mapinstalled', c_uint32), ('map_state', c_uint32),
                    ('all_event_masks', c_ulong), ('your_event_mask', c_ulong),
                    ('do_not_propagate_mask', c_ulong),
                    ('override_redirect', c_int32), ('screen', c_ulong)]

    class XImage(Structure):
        _fields_ = [('width', c_int), ('height', c_int), ('xoffset', c_int),
                    ('format', c_int), ('data', c_void_p),
                    ('byte_order', c_int), ('bitmap_unit', c_int),
                    ('bitmap_bit_order', c_int), ('bitmap_pad', c_int),
                    ('depth', c_int), ('bytes_per_line', c_int),
                    ('bits_per_pixel', c_int), ('red_mask', c_ulong),
                    ('green_mask', c_ulong), ('blue_mask', c_ulong)]

    class XRRModeInfo(Structure):
        pass

    class XRRScreenResources(Structure):
        _fields_ = [('timestamp', c_ulong), ('configTimestamp', c_ulong),
                    ('ncrtc', c_int), ('crtcs', POINTER(c_long)),
                    ('noutput', c_int), ('outputs', POINTER(c_long)),
                    ('nmode', c_int), ('modes', POINTER(XRRModeInfo))]

    class XRRCrtcInfo(Structure):
        _fields_ = [('timestamp', c_ulong), ('x', c_int), ('y', c_int),
                    ('width', c_int), ('height', c_int), ('mode', c_long),
                    ('rotation', c_int), ('noutput', c_int),
                    ('outputs', POINTER(c_long)), ('rotations', c_ushort),
                    ('npossible', c_int), ('possible', POINTER(c_long))]
elif system() == 'Windows':
    from ctypes import c_void_p, create_string_buffer, sizeof, \
        windll, Structure, POINTER, WINFUNCTYPE
    from ctypes.wintypes import BOOL, DOUBLE, DWORD, HBITMAP, HDC, \
        HGDIOBJ, HWND, INT, LPARAM, LONG, RECT, UINT, WORD

    class BITMAPINFOHEADER(Structure):
        _fields_ = [('biSize', DWORD), ('biWidth', LONG), ('biHeight', LONG),
                    ('biPlanes', WORD), ('biBitCount', WORD),
                    ('biCompression', DWORD), ('biSizeImage', DWORD),
                    ('biXPelsPerMeter', LONG), ('biYPelsPerMeter', LONG),
                    ('biClrUsed', DWORD), ('biClrImportant', DWORD)]

    class BITMAPINFO(Structure):
        _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', DWORD * 3)]
else:
    err = 'MSS: system "{0}" not implemented.'.format(system())
    raise ScreenshotError(err)


# ----------------------------------------------------------------------
# --- [ C'est parti mon kiki ! ] ---------------------------------------
# ----------------------------------------------------------------------
class MSS(object):
    ''' This class will be overloaded by a system specific one. '''

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.

            If the monitor has rotation, you have to deal with it
            inside this method.

            Parameters:
             - screen - int - grab one screenshot of all monitors (screen=-1)
                              grab one screenshot by monitor (screen=0)
                              grab the screenshot of the monitor N (screen=N)

            Returns a dict:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        '''
        raise NotImplementedError('MSS: subclasses need to implement this!')

    def get_pixels(self, monitor):
        ''' Retrieve screen pixels for a given monitor.

            `monitor` is a dict with:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'heigth': the height
            }
        '''
        raise NotImplementedError('MSS: subclasses need to implement this!')

    def save(self,
             output='screenshot-%d.png',
             screen=0,
             callback=lambda *x: True):
        ''' Grab a screenshot and save it to a file.

            Parameters:
             - output - string - the output filename. It can contain '%d' which
                                 will be replaced by the monitor number.
             - screen - int - grab one screenshot of all monitors (screen=-1)
                              grab one screenshot by monitor (screen=0)
                              grab the screenshot of the monitor N (screen=N)
             - callback - function - in case where output already exists, call
                                     the defined callback function with output
                                     as parameter. If it returns True, then
                                     continue; else ignores the monitor and
                                     switches to ne next.

            This is a generator which returns created files.
        '''

        # Monitors screen shots!
        for i, monitor in enumerate(self.enum_display_monitors(screen)):
            if screen <= 0 or (screen > 0 and i + 1 == screen):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i + 1))
                callback(fname)
                self.to_png(data=self.get_pixels(monitor),
                            width=monitor[b'width'],
                            height=monitor[b'height'],
                            output=fname)
                yield fname

    def to_png(self, data, width, height, output):
        ''' Dump data to the image file.
            Pure python PNG implementation.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        with open(output, 'wb') as fileh:
            b = pack
            line = (width * 3 + 3) & -4
            padding = 0 if line % 8 == 0 else (line % 8) // 2
            scanlines = b''.join(
                [b'0' + data[y * line:y * line + line - padding]
                 for y in range(height)])

            magic = b(b'>8B', 137, 80, 78, 71, 13, 10, 26, 10)

            # Header: size, marker, data, CRC32
            ihdr = [b'', b'IHDR', b'', b'']
            ihdr[2] = b(b'>2I5B', width, height, 8, 2, 0, 0, 0)
            ihdr[3] = b(b'>I', crc32(b''.join(ihdr[1:3])) & 0xffffffff)
            ihdr[0] = b(b'>I', len(ihdr[2]))

            # Data: size, marker, data, CRC32
            idat = [b'', b'IDAT', compress(scanlines), b'']
            idat[3] = b(b'>I', crc32(b''.join(idat[1:3])) & 0xffffffff)
            idat[0] = b(b'>I', len(idat[2]))

            # Footer: size, marker, None, CRC32
            iend = b'4IEND'

            fileh.write(magic + b''.join(ihdr) + b''.join(idat) + iend)
            return

        err = 'MSS: error writing data to "{0}".'.format(output)
        raise ScreenshotError(err)


class MSSMac(MSS):
    ''' Mutliple ScreenShots implementation for Mac OS X.
        It uses intensively the Quartz.
    '''

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        if screen == -1:
            rect = CGRectInfinite
            yield {
                b'left': int(rect.origin.x),
                b'top': int(rect.origin.y),
                b'width': int(rect.size.width),
                b'height': int(rect.size.height)
            }
        else:
            max_displays = 32  # Could be augmented, if needed ...
            rotations = {0.0: 'normal', 90.0: 'right', -90.0: 'left'}
            _, ids, _ = CGGetActiveDisplayList(max_displays, None, None)
            for display in ids:
                rect = CGRectStandardize(CGDisplayBounds(display))
                left, top = rect.origin.x, rect.origin.y
                width, height = rect.size.width, rect.size.height
                rot = CGDisplayRotation(display)
                if rotations[rot] in ['left', 'right']:
                    width, height = height, width
                yield {
                    b'left': int(left),
                    b'top': int(top),
                    b'width': int(width),
                    b'height': int(height)
                }

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB.
        '''

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        rect = CGRect((left, top), (width, height))
        options = kCGWindowListOptionOnScreenOnly
        winid = kCGNullWindowID
        default = kCGWindowImageDefault
        self.image = CGWindowListCreateImage(rect, options, winid, default)
        if not self.image:
            raise ScreenshotError('MSS: CGWindowListCreateImage() failed.')
        return self.image

    def to_png(self, data, width, height, output):
        ''' Use of internal tools, faster and less code to write :) '''

        url = NSURL.fileURLWithPath_(output)
        dest = CGImageDestinationCreateWithURL(url, kUTTypePNG, 1, None)
        if not dest:
            err = 'MSS: CGImageDestinationCreateWithURL() failed.'
            raise ScreenshotError(err)

        CGImageDestinationAddImage(dest, data, None)
        if CGImageDestinationFinalize(dest):
            return True
        raise ScreenshotError('MSS: CGImageDestinationFinalize() failed.')


class MSSLinux(MSS):
    ''' Mutliple ScreenShots implementation for GNU/Linux.
        It uses intensively the Xlib and Xrandr.
    '''

    def __del__(self):
        ''' Disconnect from X server. '''

        try:
            if self.display:
                self.xlib.XCloseDisplay(self.display)
        except AttributeError:
            pass

    def __init__(self):
        ''' GNU/Linux initialisations.

            Paths where the MSS library is loaded from:
                - /usr/local/lib/pythonx.y/dist-packages/
                - current working directory
            if no one found, use of the _very_ slow method get_pixels_slow().
        '''

        disp = None
        self.display = None
        try:
            if sys.version > '3':
                disp = bytes(environ['DISPLAY'], 'utf-8')
            else:
                disp = environ['DISPLAY']
        except KeyError:
            err = 'MSS: $DISPLAY not set. Stopping to prevent segfault.'
            raise ScreenshotError(err)

        x11 = find_library('X11')
        if not x11:
            raise ScreenshotError('MSS: no X11 library found.')
        self.xlib = cdll.LoadLibrary(x11)

        xrandr = find_library('Xrandr')
        if not xrandr:
            raise ScreenshotError('MSS: no Xrandr library found.')
        self.xrandr = cdll.LoadLibrary(xrandr)

        v_maj, v_min, _, _, _ = sys.version_info
        lib_dir = '/usr/local/lib/python{0}.{1}/dist-packages'.format(v_maj,
                                                                      v_min)
        libmss = '{0}/libmss.so'.format(lib_dir)
        try:
            self.mss = cdll.LoadLibrary(libmss)
        except OSError:
            try:
                libmss = '{0}/libmss.cpython-{1}{2}m.so'.format(lib_dir, v_maj,
                                                                v_min)
                self.mss = cdll.LoadLibrary(libmss)
            except OSError:
                try:
                    libmss = find_library('mss')
                    self.mss = cdll.LoadLibrary(libmss)
                except OSError:
                    msg = 'MSS: no MSS library found. ' + \
                          'Using slow native function.'
                    print(msg)
                    self.mss = False

        self._set_argtypes()
        self._set_restypes()

        # At this point, if there is no running server, it could end on
        # a segmentation fault. And we cannot catch it.
        self.display = self.xlib.XOpenDisplay(disp)
        self.screen = self.xlib.XDefaultScreen(self.display)
        self.root = self.xlib.XDefaultRootWindow(self.display, self.screen)

    def _set_argtypes(self):
        ''' Functions arguments.

            Curiously, if we set up self.xlib.XGetPixel.argtypes,
            the entire process takes twice more time.
            So, no need to waste this precious time :)
        '''

        self.xlib.XOpenDisplay.argtypes = [c_char_p]
        self.xlib.XDefaultScreen.argtypes = [POINTER(Display)]
        self.xlib.XDefaultRootWindow.argtypes = [POINTER(Display), c_int]
        self.xlib.XGetWindowAttributes.argtypes = [POINTER(Display),
                                                   POINTER(XWindowAttributes),
                                                   POINTER(XWindowAttributes)]
        self.xlib.XAllPlanes.argtypes = []
        self.xlib.XGetImage.argtypes = [POINTER(Display), POINTER(Display),
                                        c_int, c_int, c_uint, c_uint, c_ulong,
                                        c_int]
        # self.xlib.XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        self.xlib.XDestroyImage.argtypes = [POINTER(XImage)]
        self.xlib.XCloseDisplay.argtypes = [POINTER(Display)]
        self.xrandr.XRRGetScreenResources.argtypes = [POINTER(Display),
                                                      POINTER(Display)]
        self.xrandr.XRRGetCrtcInfo.argtypes = [POINTER(Display),
                                               POINTER(XRRScreenResources),
                                               c_long]
        self.xrandr.XRRFreeScreenResources.argtypes = \
            [POINTER(XRRScreenResources)]
        self.xrandr.XRRFreeCrtcInfo.argtypes = [POINTER(XRRCrtcInfo)]
        if self.mss:
            self.mss.GetXImagePixels.argtypes = [POINTER(XImage), c_uint,
                                                 c_uint, c_uint, c_uint,
                                                 c_uint, c_void_p]

    def _set_restypes(self):
        ''' Functions return type.

            Curiously, if we set up self.xlib.XGetPixel.restype,
            the entire process takes twice more time.
            So, no need to waste this precious time :)
        '''

        self.xlib.XOpenDisplay.restype = POINTER(Display)
        self.xlib.XDefaultScreen.restype = c_int
        self.xlib.XGetWindowAttributes.restype = c_int
        self.xlib.XAllPlanes.restype = c_ulong
        self.xlib.XGetImage.restype = POINTER(XImage)
        # self.xlib.XGetPixel.restype = c_ulong
        self.xlib.XDestroyImage.restype = c_void_p
        self.xlib.XCloseDisplay.restype = c_void_p
        self.xlib.XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.xrandr.XRRGetScreenResources.restype = POINTER(XRRScreenResources)
        self.xrandr.XRRGetCrtcInfo.restype = POINTER(XRRCrtcInfo)
        self.xrandr.XRRFreeScreenResources.restype = c_void_p
        self.xrandr.XRRFreeCrtcInfo.restype = c_void_p
        if self.mss:
            self.mss.GetXImagePixels.restype = c_void_p

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        if screen == -1:
            gwa = XWindowAttributes()
            self.xlib.XGetWindowAttributes(self.display, self.root, byref(gwa))
            yield {
                b'left': int(gwa.x),
                b'top': int(gwa.y),
                b'width': int(gwa.width),
                b'height': int(gwa.height)
            }
        else:
            # Fix for XRRGetScreenResources:
            # expected LP_Display instance instead of LP_XWindowAttributes
            root = cast(self.root, POINTER(Display))
            mon = self.xrandr.XRRGetScreenResources(self.display, root)
            for num in range(mon.contents.ncrtc):
                crtc = self.xrandr.XRRGetCrtcInfo(self.display, mon,
                                                  mon.contents.crtcs[num])
                yield {
                    b'left': int(crtc.contents.x),
                    b'top': int(crtc.contents.y),
                    b'width': int(crtc.contents.width),
                    b'height': int(crtc.contents.height)
                }
                self.xrandr.XRRFreeCrtcInfo(crtc)
            self.xrandr.XRRFreeScreenResources(mon)

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB. '''

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        ZPixmap = 2
        allplanes = self.xlib.XAllPlanes()

        # Fix for XGetImage:
        # expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        ximage = self.xlib.XGetImage(self.display, root, left, top, width,
                                     height, allplanes, ZPixmap)
        if not ximage:
            raise ScreenshotError('MSS: XGetImage() failed.')

        if not self.mss:
            self.image = self.get_pixels_slow(ximage, width, height,
                                              ximage.contents.red_mask,
                                              ximage.contents.green_mask,
                                              ximage.contents.blue_mask)
        else:
            buffer_len = height * width * 3
            self.image = create_string_buffer(buffer_len)
            self.mss.GetXImagePixels(ximage, width, height,
                                     ximage.contents.red_mask,
                                     ximage.contents.green_mask,
                                     ximage.contents.blue_mask, self.image)
        self.xlib.XDestroyImage(ximage)
        return self.image

    def get_pixels_slow(self, ximage, width, height, rmask, gmask, bmask):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB.

            /!\ Insanely slow version using ctypes.

            The XGetPixel() C code can be found at this URL:
            http://cgit.freedesktop.org/xorg/lib/libX11/tree/src/ImUtil.c#n444


            @TODO: see if it is quicker than using XGetPixel().

            1) C code as quick as XGetPixel() to translate into ctypes:

            pixels = malloc(sizeof(unsigned char) * width * height * 3);
            for ( x = 0; x < width; ++x )
                for ( y = 0; y < height; ++y )
                    offset =  width * y * 3;
                    addr = &(ximage->data)[y * ximage->bytes_per_line + (x << 2)];
                    pixel = addr[3] << 24 | addr[2] << 16 | addr[1] << 8 | addr[0];
                    pixels[x * 3 + offset]     = (pixel & ximage->red_mask) >> 16;
                    pixels[x * 3 + offset + 1] = (pixel & ximage->green_mask) >> 8;
                    pixels[x * 3 + offset + 2] =  pixel & ximage->blue_mask;

            2) A first try in Python with ctypes

            from ctypes import create_string_buffer, c_char
            rmask = ximage.contents.red_mask
            gmask = ximage.contents.green_mask
            bmask = ximage.contents.blue_mask
            bpl = ximage.contents.bytes_per_line
            buffer_len = width * height * 3
            xdata = ximage.contents.data
            data = cast(xdata, POINTER(c_char * buffer_len)).contents
            self.image = create_string_buffer(sizeof(c_char) * buffer_len)
            for x in range(width):
                for y in range(height):
                    offset =  x * 3 + width * y * 3
                    addr = data[y * bpl + (x << 2)][0]
                    pixel = addr[3] << 24 | addr[2] << 16 | addr[1] << 8 | addr[0]
                    self.image[offset]     = (pixel & rmask) >> 16
                    self.image[offset + 1] = (pixel & gmask) >> 8
                    self.image[offset + 2] =  pixel & bmask
            return self.image
        '''

        # @TODO: this part takes most of the time. Need a better solution.
        def pix(pixel, _resultats={}, _b=pack):
            ''' Apply shifts to a pixel to get the RGB values.
                This method uses of memoization.
            '''
            if pixel not in _resultats:
                _resultats[pixel] = _b(b'<B', (pixel & rmask) >> 16) + \
                    _b(b'<B', (pixel & gmask) >> 8) + _b(b'<B', pixel & bmask)
            return _resultats[pixel]

        get_pix = self.xlib.XGetPixel
        pixels = [pix(get_pix(ximage, x, y))
                  for y in range(height) for x in range(width)]
        self.image = b''.join(pixels)
        return self.image


class MSSWindows(MSS):
    ''' Mutliple ScreenShots implementation for Microsoft Windows. '''

    def __init__(self):
        ''' Windows initialisations. '''

        self._set_argtypes()
        self._set_restypes()

    def _set_argtypes(self):
        ''' Functions arguments. '''

        self.MONITORENUMPROC = WINFUNCTYPE(INT, DWORD, DWORD, POINTER(RECT),
                                           DOUBLE)
        windll.user32.GetSystemMetrics.argtypes = [INT]
        windll.user32.EnumDisplayMonitors.argtypes = [HDC, c_void_p,
                                                      self.MONITORENUMPROC,
                                                      LPARAM]
        windll.user32.GetWindowDC.argtypes = [HWND]
        windll.gdi32.CreateCompatibleDC.argtypes = [HDC]
        windll.gdi32.CreateCompatibleBitmap.argtypes = [HDC, INT, INT]
        windll.gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
        windll.gdi32.BitBlt.argtypes = [HDC, INT, INT, INT, INT, HDC, INT, INT,
                                        DWORD]
        windll.gdi32.DeleteObject.argtypes = [HGDIOBJ]
        windll.gdi32.GetDIBits.argtypes = [HDC, HBITMAP, UINT, UINT, c_void_p,
                                           POINTER(BITMAPINFO), UINT]

    def _set_restypes(self):
        ''' Functions return type. '''

        windll.user32.GetSystemMetrics.restypes = INT
        windll.user32.EnumDisplayMonitors.restypes = BOOL
        windll.user32.GetWindowDC.restypes = HDC
        windll.gdi32.CreateCompatibleDC.restypes = HDC
        windll.gdi32.CreateCompatibleBitmap.restypes = HBITMAP
        windll.gdi32.SelectObject.restypes = HGDIOBJ
        windll.gdi32.BitBlt.restypes = BOOL
        windll.gdi32.GetDIBits.restypes = INT
        windll.gdi32.DeleteObject.restypes = BOOL

    def enum_display_monitors(self, screen=-1):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        if screen == -1:
            SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
            SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
            left = windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            right = windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            top = windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            bottom = windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            yield {
                b'left': int(left),
                b'top': int(top),
                b'width': int(right - left),
                b'height': int(bottom - top)
            }
        else:

            def _callback(monitor, dc, rect, data):
                ''' Callback for MONITORENUMPROC() function, it will return
                    a RECT with appropriate values.
                '''
                rct = rect.contents
                monitors.append({
                    b'left': int(rct.left),
                    b'top': int(rct.top),
                    b'width': int(rct.right - rct.left),
                    b'height': int(rct.bottom - rct.top)
                })
                return 1

            monitors = []
            callback = self.MONITORENUMPROC(_callback)
            windll.user32.EnumDisplayMonitors(0, 0, callback, 0)
            for mon in monitors:
                yield mon

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB.

            [1] A bottom-up DIB is specified by setting the height to a
            positive number, while a top-down DIB is specified by
            setting the height to a negative number.
            https://msdn.microsoft.com/en-us/library/ms787796.aspx
            https://msdn.microsoft.com/en-us/library/dd144879%28v=vs.85%29.aspx
        '''

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        SRCCOPY = 0xCC0020
        DIB_RGB_COLORS = BI_RGB = 0
        srcdc = memdc = bmp = None

        try:
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # Why minus? See [1]
            bmi.bmiHeader.biPlanes = 1  # Always 1
            bmi.bmiHeader.biBitCount = 24
            bmi.bmiHeader.biCompression = BI_RGB
            buffer_len = height * width * 3
            self.image = create_string_buffer(buffer_len)
            srcdc = windll.user32.GetWindowDC(0)
            memdc = windll.gdi32.CreateCompatibleDC(srcdc)
            bmp = windll.gdi32.CreateCompatibleBitmap(srcdc, width, height)
            windll.gdi32.SelectObject(memdc, bmp)
            windll.gdi32.BitBlt(memdc, 0, 0, width, height, srcdc, left, top,
                                SRCCOPY)
            bits = windll.gdi32.GetDIBits(memdc, bmp, 0, height, self.image,
                                          bmi, DIB_RGB_COLORS)
            if bits != height:
                raise ScreenshotError('MSS: GetDIBits() failed.')
        finally:
            # Clean up
            if srcdc:
                windll.gdi32.DeleteObject(srcdc)
            if memdc:
                windll.gdi32.DeleteObject(memdc)
            if bmp:
                windll.gdi32.DeleteObject(bmp)

        # Replace pixels values: BGR to RGB
        self.image = bytearray(self.image)
        self.image[2:buffer_len:3], self.image[0:buffer_len:3] = \
            self.image[0:buffer_len:3], self.image[2:buffer_len:3]
        self.image = bytes(self.image)
        return self.image


def mss(*args, **kwargs):
    ''' Factory returning a proper MSS class instance.

        It detects the plateform we are running on
        and choose the most adapted mss_class to take
        screenshots.

        It then proxies its arguments to the class for
        instantiation.
    '''

    mss_class = {'Darwin': MSSMac,
                 'Linux': MSSLinux,
                 'Windows': MSSWindows}[system()]

    return mss_class(*args, **kwargs)


def main():
    ''' Usage example. '''

    def on_exists(fname):
        ''' Callback example when we try to overwrite an existing
            screenshot.
        '''
        from os import rename
        from os.path import isfile
        if isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            rename(fname, newfile)
        return True

    try:
        screenshotter = mss()

        print('One screenshot per monitor')
        for filename in screenshotter.save():
            print(filename)

        print("\nScreenshot of the monitor 1")
        for filename in screenshotter.save(output='monitor-%d.png', screen=1):
            print(filename)

        print("\nA screenshot to grab them all")
        for filename in screenshotter.save(output='fullscreen.png', screen=-1):
            print(filename)

        print("\nScreenshot of the monitor 1, with callback")
        for filename in screenshotter.save(output='mon-%d.png',
                                           screen=1,
                                           callback=on_exists):
            print(filename)
    except ScreenshotError as ex:
        print(ex)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
