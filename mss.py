#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' An attempt to create a full functionnal multi-screen shot module
    in _pure_ python using ctypes.

    This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.
    If you find problems, please submit bug reports/patches via the
    GitHub issue tracker (https://github.com/BoboTiG/python-mss/issues).

    Note: please keep this module compatible to Python 2.6.

    Still needed:
    * support for PNG format
    * support for additional systems

    Many thanks to all those who helped (in no particular order):

      toi, moi, le pape et les autres

    History:

    <see Git checkin messages for history>

    0.0.1 - first release

    You can always get the latest version of this module at:

             https://raw.github.com/BoboTiG/python-mss/mss.py

    If that URL should fail, try contacting the author.
'''

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '0.0.1'
__author__ = "Mickaël 'Tiger-222' Schoentgen"
__copyright__ = '''
    Copyright (c) 2013, Mickaël 'Tiger-222' Schoentgen

    Permission to use, copy, modify, and distribute this software and its
    documentation for any purpose and without fee or royalty is hereby
    granted, provided that the above copyright notice appear in all copies
    and that both that copyright notice and this permission notice appear
    in supporting documentation or portions thereof, including
    modifications, that you make.
'''
__all__ = ['MSS', 'MSSImage']


from ctypes.util import find_library
from struct import calcsize, pack
from os.path import isfile
import zlib
from platform import system

if system() == 'Linux':
    from ctypes import addressof, byref, cast, cdll
    from ctypes import (
        c_char_p,
        c_int,
        c_int32,
        c_uint,
        c_uint32,
        c_ulong,
        c_void_p,
        POINTER,
        Structure
    )

    class Display(Structure):
        pass

    class XWindowAttributes(Structure):
        _fields_ = [
            ("x",                     c_int32),
            ("y",                     c_int32),
            ("width",                 c_int32),
            ("height",                c_int32),
            ("border_width",          c_int32),
            ("depth",                 c_int32),
            ("visual",                c_ulong),
            ("root",                  c_ulong),
            ("class",                 c_int32),
            ("bit_gravity",           c_int32),
            ("win_gravity",           c_int32),
            ("backing_store",         c_int32),
            ("backing_planes",        c_ulong),
            ("backing_pixel",         c_ulong),
            ("save_under",            c_int32),
            ("colourmap",             c_ulong),
            ("mapinstalled",          c_uint32),
            ("map_state",             c_uint32),
            ("all_event_masks",       c_ulong),
            ("your_event_mask",       c_ulong),
            ("do_not_propagate_mask", c_ulong),
            ("override_redirect",     c_int32),
            ("screen",                c_ulong)
        ]

    class XImage(Structure):
        _fields_ = [
            ('width'            , c_int),
            ('height'           , c_int),
            ('xoffset'          , c_int),
            ('format'           , c_int),
            ('data'             , c_char_p),
            ('byte_order'       , c_int),
            ('bitmap_unit'      , c_int),
            ('bitmap_bit_order' , c_int),
            ('bitmap_pad'       , c_int),
            ('depth'            , c_int),
            ('bytes_per_line'   , c_int),
            ('bits_per_pixel'   , c_int),
            ('red_mask'         , c_ulong),
            ('green_mask'       , c_ulong),
            ('blue_mask'        , c_ulong)
        ]

elif system() == 'Windows':
    from ctypes import byref, memset, pointer, sizeof, windll
    from ctypes.wintypes import (
        c_void_p as LPRECT,
        c_void_p as LPVOID,
        create_string_buffer,
        Structure,
        BOOL,
        DOUBLE,
        DWORD,
        HANDLE,
        HBITMAP,
        HDC,
        HGDIOBJ,
        HWND,
        INT,
        LPARAM,
        LONG,
        POINTER,
        RECT,
        SHORT,
        UINT,
        WINFUNCTYPE,
        WORD
    )

    class BITMAPINFOHEADER(Structure):
        _fields_ = [
            ('biSize',          DWORD),
            ('biWidth',         LONG),
            ('biHeight',        LONG),
            ('biPlanes',        WORD),
            ('biBitCount',      WORD),
            ('biCompression',   DWORD),
            ('biSizeImage',     DWORD),
            ('biXPelsPerMeter', LONG),
            ('biYPelsPerMeter', LONG),
            ('biClrUsed',       DWORD),
            ('biClrImportant',  DWORD)
        ]

    class BITMAPINFO(Structure):
        _fields_ = [
            ('bmiHeader', BITMAPINFOHEADER),
            ('bmiColors', DWORD * 3)
        ]



# ----------------------------------------------------------------------
# --- [ C'est parti mon kiki ! ] ---------------------------------------
# ----------------------------------------------------------------------

class MSS(object):
    ''' This class will be overloaded by a system specific one.
    It checkes if there is a class available for the current system.
    Raise an exception if no one found.
    '''

    DEBUG = True

    def __init__(self):
        ''' Global vars and class overload. '''

        self.monitors = ()
        self.oneshot = False

        this_is = system()
        self.debug('__init__', 'system', this_is)
        self.debug('__init__', 'oneshot', self.oneshot)

        if this_is == 'Linux':
            self.__class__ = MSSLinux
        elif this_is == 'Windows':
            self.__class__ = MSSWindows
        else:
            err = 'System "{0}" not implemented.'.format(this_is)
            raise NotImplementedError(err)

        self.init()

    def debug(self, method='', scalar='', value=None):
        ''' Simple debug output. '''

        if self.DEBUG:
            print(method + '()', scalar, value)

    def save(self, output='mss', oneshot=False, ext='jpg'):
        ''' For each monitor, grab a screen shot and save it to a file.

            Parameters:
             - output - string - the output filename without extension
             - oneshot - boolean -grab only one screen shot of all monitors
             - ext - string - file format to save

            This is a generator which returns created files:
                'output-1.ext',
                'output-2.ext',
                ...,
                'output-NN.ext'
                or
                'output-full.ext'
        '''

        self.oneshot = oneshot
        self.monitors = self._enum_display_monitors() or []

        if len(self.monitors) < 1:
            raise ValueError('MSS: no monitor found.')

        # Monitors screen shots!
        i = 1
        for monitor in self.monitors:
            self.debug('save', 'monitor', monitor)

            if self.oneshot:
                filename = output + '-full'
            else:
                filename = output + '-' + str(i)
                i += 1
            monitor['width'] = monitor['right'] - monitor['left']
            monitor['height'] = monitor['bottom'] - monitor['top']

            pixels = self._get_pixels(monitor)
            if pixels is None:
                raise ValueError('MSS: no data to process.')

            img = MSSImage(pixels, monitor['width'], monitor['height'])
            img.dump(filename, ext=ext)
            if img.output is not None and isfile(img.output):
                yield img.output

    def _enum_display_monitors(self):
        '''
            Get positions of all monitors.

            If self.oneshot is True, this function has to return a dict
            with dimensions of all monitors at the same time.

            Must returns a dict with a minima:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'right':  the x-coordinate of the lower-right corner,
                'bottom': the y-coordinate of the lower-right corner
            }
        '''
        pass

    def _get_pixels(self, monitor_infos):
        '''
            Retrieve screen pixels for a given monitor.

            monitor_infos should contain at least:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'right':  the x-coordinate of the lower-right corner,
                'bottom': the y-coordinate of the lower-right corner
                'width':  the width,
                'heigth': the height
            }

            Returns a dict with pixels.

        '''
        pass


class MSSLinux(MSS):
    '''
        Mutli-screen shot implementation for GNU/Linux.
        It uses intensively the Xlib.
    '''

    def init(self):
        ''' GNU/Linux initialisations '''

        x11 = find_library('X11')
        if x11 is None:
            raise OSError('MSSLinux: no X11 library found.')
        else:
            xlib = cdll.LoadLibrary(x11)

        # Acces to the X server
        XOpenDisplay = xlib.XOpenDisplay
        XOpenDisplay.argtypes = [c_char_p]
        XOpenDisplay.restype = POINTER(Display)
        self.XOpenDisplay = XOpenDisplay

        #
        XDefaultRootWindow = xlib.XDefaultRootWindow
        XDefaultRootWindow.argtypes = [POINTER(Display)]
        XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.XDefaultRootWindow = XDefaultRootWindow

        #
        XGetWindowAttributes = xlib.XGetWindowAttributes
        XGetWindowAttributes.argtypes = [POINTER(Display),
                POINTER(XWindowAttributes), POINTER(XWindowAttributes)]
        XGetWindowAttributes.restype = c_int
        self.XGetWindowAttributes = XGetWindowAttributes

        #
        XAllPlanes = xlib.XAllPlanes
        XAllPlanes.argtypes = []
        XAllPlanes.restype = c_ulong
        self.XAllPlanes = XAllPlanes

        #
        XGetImage = xlib.XGetImage
        XGetImage.argtypes = [POINTER(Display), POINTER(Display),
                            c_int, c_int, c_uint, c_uint, c_ulong, c_int]
        XGetImage.restype = POINTER(XImage)
        self.XGetImage = xlib.XGetImage

        #
        XGetPixel = xlib.XGetPixel
        XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        XGetPixel.restype = c_ulong
        self.XGetPixel = XGetPixel

        # Constants and scalars
        self.ZPixmap = 2
        self.display = self.XOpenDisplay(None)
        self.root = self.XDefaultRootWindow(self.display)

    def _enum_display_monitors(self):
        '''
            Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        results = []
        if self.oneshot:
            gwa = XWindowAttributes()
            self.XGetWindowAttributes(self.display, self.root, byref(gwa))
            infos = {b'left': gwa.x, b'right': gwa.width,
                    b'top': gwa.y, b'bottom': gwa.height}
            results.append(infos)
        return results

    def _get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB. '''

        width, height = monitor['width'], monitor['height']
        left, top = monitor['left'], monitor['top']

        return None
        allplanes = self.XAllPlanes()
        self.debug('_get_pixels', 'allplanes', allplanes)

        '''
        XImage *image = XGetImage(display,root, 0,0 , width,height,AllPlanes, ZPixmap);

        unsigned char *array = new unsigned char[width * height * 3];

        unsigned long red_mask = image->red_mask;
        unsigned long green_mask = image->green_mask;
        unsigned long blue_mask = image->blue_mask;

        for (int x = 0; x < width; x++)
          for (int y = 0; y < height ; y++)
          {
             unsigned long pixel = XGetPixel(image,x,y);

             unsigned char blue = pixel & blue_mask;
             unsigned char green = (pixel & green_mask) >> 8;
             unsigned char red = (pixel & red_mask) >> 16;

             array[(x + width * y) * 3] = red;
             array[(x + width * y) * 3+1] = green;
             array[(x + width * y) * 3+2] = blue;
          }
        '''
        self.root = self.XDefaultRootWindow(self.display)
        # Fix for XGetImage: expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        image = self.XGetImage(self.display, root, 0, 0, width, height,
                                allplanes, self.ZPixmap)
        if image is None:
            raise ValueError('MSSLinux: XGetImage() failed.')

        pixels = b''
        for x in range(width):
            for y in range(height):
                pixel = self.XGetPixel(image, x, y)
                b, g, r = pixel & 255, (pixel & 65280) >> 8, (pixel & 16711680) >> 16
                offset = (x + width * y) * 3
                pixels += bytes(r)
                pixels += bytes(g)
                pixels += bytes(b)
        return pixels


class MSSWindows(MSS):
    ''' Mutli-screen shot implementation for Microsoft Windows. '''

    def init(self):
        ''' Windows initialisations '''

        self.SM_XVIRTUALSCREEN = 76
        self.SM_YVIRTUALSCREEN = 77
        self.SM_CXVIRTUALSCREEN = 78
        self.SM_CYVIRTUALSCREEN = 79
        self.SRCCOPY = 0xCC0020
        self.DIB_RGB_COLORS = 0

        self.GetSystemMetrics = windll.user32.GetSystemMetrics
        self.EnumDisplayMonitors = windll.user32.EnumDisplayMonitors
        self.GetWindowDC = windll.user32.GetWindowDC
        self.CreateCompatibleDC = windll.gdi32.CreateCompatibleDC
        self.CreateCompatibleBitmap = windll.gdi32.CreateCompatibleBitmap
        self.SelectObject = windll.gdi32.SelectObject
        self.BitBlt = windll.gdi32.BitBlt
        self.GetDIBits = windll.gdi32.GetDIBits
        self.DeleteObject = windll.gdi32.DeleteObject

        self._set_argtypes()
        self._set_restypes()

    def _set_argtypes(self):
        ''' Functions arguments '''

        self.MONITORENUMPROC = WINFUNCTYPE(INT, DWORD, DWORD,
                                            POINTER(RECT), DOUBLE)
        self.GetSystemMetrics.argtypes = [INT]
        self.EnumDisplayMonitors.argtypes = [HDC, LPRECT, self.MONITORENUMPROC, LPARAM]
        self.GetWindowDC.argtypes = [HWND]
        self.CreateCompatibleDC.argtypes = [HDC]
        self.CreateCompatibleBitmap.argtypes = [HDC, INT, INT]
        self.SelectObject.argtypes = [HDC, HGDIOBJ]
        self.BitBlt.argtypes = [HDC, INT, INT, INT, INT, HDC, INT, INT, DWORD]
        self.DeleteObject.argtypes = [HGDIOBJ]
        self.GetDIBits.argtypes = [HDC, HBITMAP, UINT, UINT, LPVOID,
                                POINTER(BITMAPINFO), UINT]

    def _set_restypes(self):
        ''' Functions return type '''

        self.GetSystemMetrics.restypes = INT
        self.EnumDisplayMonitors.restypes = BOOL
        self.GetWindowDC.restypes = HDC
        self.CreateCompatibleDC.restypes = HDC
        self.CreateCompatibleBitmap.restypes = HBITMAP
        self.SelectObject.restypes = HGDIOBJ
        self.BitBlt.restypes =  BOOL
        self.GetDIBits.restypes = INT
        self.DeleteObject.restypes = BOOL

    def _enum_display_monitors(self):
        '''
            Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        def _callback(monitor, dc, rect, data):
            rct = rect.contents
            infos = {'left': int(rct.left), 'right': int(rct.right),
                    'top': int(rct.top), 'bottom': int(rct.bottom)}
            results.append(infos)
            return 1

        results = []
        if self.oneshot:
            left = self.GetSystemMetrics(self.SM_XVIRTUALSCREEN)
            right = self.GetSystemMetrics(self.SM_CXVIRTUALSCREEN)
            top = self.GetSystemMetrics(self.SM_YVIRTUALSCREEN)
            bottom = self.GetSystemMetrics(self.SM_CYVIRTUALSCREEN)
            results.append({'left': int(left), 'right': int(right),
                            'top': int(top), 'bottom': int(bottom)})
        else:
            callback = self.MONITORENUMPROC(_callback)
            self.EnumDisplayMonitors(0, 0, callback, 0)
        return results

    def _get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB. '''

        width, height = monitor['width'], monitor['height']
        left, top = monitor['left'], monitor['top']

        srcdc = self.GetWindowDC(0)
        memdc = self.CreateCompatibleDC(srcdc)
        bmp = self.CreateCompatibleBitmap(srcdc, width, height)
        self.SelectObject(memdc, bmp)
        self.BitBlt(memdc, 0, 0, width, height, srcdc, left, top,
                    self.SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = height
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biPlanes = 1
        buffer_len = height * ((width * 3 + 3) & -4)
        pixels = create_string_buffer(buffer_len)
        bits = self.GetDIBits(memdc, bmp, 0, height, byref(pixels),
                                pointer(bmi), self.DIB_RGB_COLORS)

        self.debug('_get_pixels', 'srcdc', srcdc)
        self.debug('_get_pixels', 'memdc', memdc)
        self.debug('_get_pixels', 'bmp', bmp)
        self.debug('_get_pixels', 'buffer_len', buffer_len)
        self.debug('_get_pixels', 'bits', bits)
        self.debug('_get_pixels', 'len(pixels.raw)', len(pixels.raw))

        # Clean up
        self.DeleteObject(srcdc)
        self.DeleteObject(memdc)
        self.DeleteObject(bmp)

        if bits != height or len(pixels.raw) != buffer_len:
            raise ValueError('MSSWindows: GetDIBits() failed.')

        # Note that the origin of the returned image is in the
        # bottom-left corner, 32-bit aligned. Need to "arrange" that.
        #data = bottom_left(pixels.raw, width, height)
        #shift = b' ' * (buffer_len - len(data))
        #data.extend(shift)

        # We need to convert BGR to RGB
        #return bgr_to_rgb(bytes(scanlines), width, height)
        data = pixels.raw
        return data


class MSSImage(object):
    ''' This is a class to save data to a picture file.
    '''

    # Known extensions
    ext_ok = [
        'libjpg',  # ctypes over libjpeg
        'libpng',  # pure python PNG implementation
        'jpg',     # JPG using external libraries (Pillow, PIL, ...)
        'png'      # PNG using external libraries (Pillow, PIL, ...)
    ]

    def __init__(self, data=None, width=1, height=1):
        ''' This method is light and should not change. It is like this
            to allow the call of extenstions() without manipulating
            real data.
        '''

        if width < 1 or height < 1:
            raise ValueError('MSSImage: width or height must be positive.')

        self.data = data
        self.width = width
        self.height = height

    def extensions(self):
        ''' List all known and working extensions. '''

        exts = []
        for ext in self.ext_ok:
            if hasattr(self, ext):
                exts.append(ext)
        exts.append('jpg, png, ..., it will try using external libraries')
        return exts

    def dump(self, output=None, ext='jpg', quality=95):
        ''' Dump data to the image file using file format specified by
            ext.
            To save time, it will try if PIL or another image library is
            available to use or it will use the wrapper to libjpeg using ctypes.
            Finally, if all fails, it will use the pure python PNG implementation.
        '''

        if self.data is None:
            raise ValueError('MSSImage: no data to process.')
        #if not isinstance(self.data, bytearray):
        #    raise ValueError('MSSImage: bad data [{0}].'.format(type(self.data)))
        #if not ext in self.ext_ok:
        #    raise ValueError('MSSImage: unknown extension.')

        self.filename = output
        self.ext = ext
        self.quality = max(0, min(quality, 100))
        self.output = None
        contents = None

        # Pure python implementations start with 'lib' (libjpg, libpng)
        if hasattr(self, self.ext):
            contents = getattr(self, self.ext)()

        # Try external libraries first
        if contents is None:
            try:
                buffer_len = (self.width * 3 + 3) & -4
                from PIL import Image, ImageFile
                tmp = self.filename + '.' + self.ext
                #img = Image.frombuffer('RGB', (self.width, self.height),
                #                        self.data, 'raw', 'BGR', buffer_len, -1)
                img = Image.frombuffer('RGB', (self.width, self.height),
                                        self.data, 'raw', 'RGB', buffer_len, 1)
                ImageFile.MAXBLOCK = self.width * self.height
                img.save(tmp, quality=self.quality, optimize=True, progressive=True)
                self.output = tmp
                return
            except Exception as ex:
                print(ex)
                pass

        # Here, no success, use pure python PNG implementation
        #if contents is None:
        #    contents = self.libpng()

        if contents is not None:
            self.output = self.filename + '.' + self.ext
            with open(self.output, 'wb') as fileh:
                fileh.write(contents)

    def libjpg(self):
        '''
            JPEG implementation using ctypes with libjpeg.
        '''
        pass

    def libpng(self):
        ''' Pure python PNG implementation.
            Image represented as RGB tuples, no interlacing.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        def filter_scanline(ftype, line, fo, prev=None):
            ''' http://pypng.googlecode.com/svn/trunk/code/png.py
                Apply a scanline filter to a scanline. `ftype` specifies the
                filter type (0 to 4); `line` specifies the current (unfiltered)
                scanline as a sequence of bytes; `prev` specifies the previous
                (unfiltered) scanline as a sequence of bytes. `fo` specifies the
                filter offset; normally this is size of a pixel in bytes (the number
                of bytes per sample times the number of channels), but when this is
                < 1 (for bit depths < 8) then the filter offset is 1.
            '''

            scanline = pack(b'B', ftype)

            def sub():
                out = b''
                ai = -fo
                for x in line:
                    if ai >= 0:
                        x = (x - line[ai]) & 0xff
                    out += pack(b'B', x)
                    ai += 1
                return out

            def up():
                out = b''
                for i, x in enumerate(line):
                    x = (x - prev[i]) & 0xff
                    out += pack(b'B', x)
                return out

            def average():
                out = b''
                ai = -fo
                for i, x in enumerate(line):
                    if ai >= 0:
                        x = (x - ((line[ai] + prev[i]) >> 1)) & 0xff
                    else:
                        x = (x - (prev[i] >> 1)) & 0xff
                    out += pack(b'B', x)
                    ai += 1
                return out

            def paeth():
                out = b''
                ai = -fo
                for i, x in enumerate(line):
                    a = 0
                    b = prev[i]
                    c = 0

                    if ai >= 0:
                        a = line[ai]
                        c = prev[ai]
                    p = a + b - c
                    pa = abs(p - a)
                    pb = abs(p - b)
                    pc = abs(p - c)
                    if pa <= pb and pa <= pc: Pr = a
                    elif pb <= pc: Pr = b
                    else: Pr = c

                    x = (x - Pr) & 0xff
                    out += pack(b'B', x)
                    ai += 1
                return out

            if not prev:
                # We're on the first line.  Some of the filters can be reduced
                # to simpler cases which makes handling the line "off the top"
                # of the image simpler.  "up" becomes "none"; "paeth" becomes
                # "left" (non-trivial, but true). "average" needs to be handled
                # specially.
                if ftype == 2: # "up"
                    return bytes(line) # type = 0
                elif ftype == 3:
                    prev = [0] * len(line)
                elif ftype == 4: # "paeth"
                    ftype = 1
            if ftype == 0:
                scanline += bytes(line)
            elif ftype == 1:
                scanline += sub()
            elif ftype == 2:
                scanline += up()
            elif ftype == 3:
                scanline += average()
            else: # type == 4
                scanline += paeth()
            return scanline

        self.ext = 'png'
        width, height, data = self.width, self.height, self.data

        to_take = (width * 3 + 3) & -4
        padding = (to_take % 32) // 2  # Fix for MS Windows 64 bits
        offset = 0
        scanlines = b''
        filter_type = 4
        prev = None
        for y in range(height):
            line = bytearray(data[offset : offset+to_take-padding])
            scanlines += filter_scanline(filter_type, line, 3, prev)
            prev = line
            offset += to_take

        magic = pack(b'>8B', 137, 80, 78, 71, 13, 10, 26, 10)

        # Header: size, marker, data, CRC32
        ihdr = [b'', b'IHDR', b'', b'']
        ihdr[2] = pack(b'>2I5B', width, height, 8, 2, 0, 0, 0)
        ihdr[3] = pack(b'>I', zlib.crc32(b''.join(ihdr[1:3])) & 0xffffffff)
        ihdr[0] = pack(b'>I', len(ihdr[2]))

        # Data: size, marker, data, CRC32
        idat = [b'', b'IDAT', b'', b'']
        idat[2] = zlib.compress(scanlines, 9)
        idat[3] = pack(b'>I', zlib.crc32(b''.join(idat[1:3])) & 0xffffffff)
        idat[0] = pack(b'>I', len(idat[2]))

        # Footer: size, marker, None, CRC32
        iend = [b'', b'IEND', b'', b'']
        iend[3] = pack(b'>I', zlib.crc32(iend[1]) & 0xffffffff)
        iend[0] = pack(b'>I', len(iend[2]))

        return magic + b''.join(ihdr) + b''.join(idat) + b''.join(iend)


def bottom_left(data, width, height):
    ''' Reorganise data when the origin of the image is in the
        bottom-left corner. '''

    scanlines = bytearray()
    y = height - 1
    while y >= 0:
        offstart = y * width * 3
        offend = ((y + 1) * width * 3)
        scanlines.extend(data[offstart:offend])
        y -= 1
    return scanlines


def bgr_to_rgb(data, width, height):
    ''' Convert BGR triple to RGB. '''

    rgb = [None] * (3 * width * height)
    for x in range(width):
        for y in range(height):
            off = 3 * (width * y + x)
            rgb[off:off+3] = data[off+2], data[off+1], data[off]
    return rgb


if __name__ == '__main__':
    #'''
    try:
        mss = MSS()
        # One screen shot per monitor
        #for filename in mss.save():
        #    print('File "{0}" created.'.format(filename))
        #for filename in mss.save(oneshot=True):
        #    print('File "{0}" created.'.format(filename))

        # A screen shot to grab them all :)
        for filename in mss.save(oneshot=True):
            print('File "{0}" created.'.format(filename))
    except Exception as ex:
        #print(ex)
        raise

    '''
    # MSSImage tests
    try:
        from os import path
        img = MSSImage()

        img.width = 1440
        img.height = 900
        with open('data.raw', 'rb') as fileh:
            data = fileh.read()

            img.data = data
            img.dump('data-output-pil', ext='png', quality=95)
            if img.output is not None:
                statinfo = path.getsize(img.output)
                print('File "{0}" created: {1}'.format(img.output, statinfo))

            img.data = data
            img.dump('data-output', ext='libpng')
            if img.output is not None:
                statinfo = path.getsize(img.output)
                print('File "{0}" created: {1}'.format(img.output, statinfo))

        print("")

        img.width = 1366
        img.height = 768
        with open('data2.raw', 'rb') as fileh:
            data = fileh.read()

            img.data = data
            img.dump('data2-output-pil', ext='png', quality=95)
            if img.output is not None:
                statinfo = path.getsize(img.output)
                print('File "{0}" created: {1}'.format(img.output, statinfo))

            img.data = data
            img.dump('data2-output', ext='libpng')
            if img.output is not None:
                statinfo = path.getsize(img.output)
                print('File "{0}" created: {1}'.format(img.output, statinfo))
    except Exception as ex:
        print(ex)
        raise
    #'''
