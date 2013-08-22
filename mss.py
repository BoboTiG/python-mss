#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' An attempt to create a full functionnal multi-screen shot module
    in _pure_ python using ctypes.

    This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.
    If you find problems, please submit bug reports/patches via the
    GitHub issue tracker (https://github.com/BoboTiG/python-mss/issues).

    Note: please keep this module compatible to Python 2.6.

    Still needed:
    * support for built-in JPEG format
    * support for additional systems

    Many thanks to all those who helped (in no particular order):

      Oros

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
__all__ = ['MSSLinux', 'MSSWindows', 'MSSImage']


from ctypes.util import find_library
from struct import pack
import zlib
from platform import system

if system() == 'Linux':
    from os import environ
    from os.path import expanduser, isfile
    import xml.etree.ElementTree as ET
    from ctypes import byref, cast, cdll
    from ctypes import (
        c_char_p, c_int, c_int32, c_uint, c_uint32,
        c_ulong, c_void_p, POINTER, Structure
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
    from ctypes import (
        byref, memset, pointer, sizeof, windll,
        c_void_p as LPRECT,
        c_void_p as LPVOID,
        create_string_buffer,
        Structure,
        POINTER,
        WINFUNCTYPE,
    )
    from ctypes.wintypes import (
        BOOL, DOUBLE, DWORD, HANDLE, HBITMAP, HDC, HGDIOBJ,
        HWND, INT, LPARAM, LONG,RECT,SHORT, UINT, WORD
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

    DEBUG = False

    def __init__(self, debug=False):
        ''' Global vars and class overload. '''

        self.DEBUG = debug
        self.monitors = []
        self.oneshot = False

        self.init()

    def debug(self, method='', scalar=None, value=None):
        ''' Simple debug output. '''

        if self.DEBUG:
            if scalar is None:
                print(':: ' + method + '()')
            else:
                print(method + '()', scalar, type(value), value)

    def save(self, output='mss', oneshot=False, ext='png', ftype=0):
        ''' For each monitor, grab a screen shot and save it to a file.

            Parameters:
             - output - string - the output filename without extension
             - oneshot - boolean -grab only one screen shot of all monitors
             - ext - string - file format to save
             - ftype - int - PNG filter type (0..4 [slower])

            This is a generator which returns created files:
                'output-1.ext',
                'output-2.ext',
                ...,
                'output-NN.ext'
                or
                'output-full.ext'
        '''

        self.debug('save')

        self.oneshot = oneshot
        self.monitors = self.enum_display_monitors() or []

        self.debug('save', 'oneshot', self.oneshot)
        self.debug('save', 'extension', ext)
        self.debug('save', 'filter_type', ftype)

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

            pixels = self.get_pixels(monitor)
            if pixels is None:
                raise ValueError('MSS: no data to process.')

            img = MSSImage(pixels, monitor[b'width'], monitor[b'height'])
            img_out = img.dump(filename, ext=ext, ftype=ftype)
            self.debug('save', 'img_out', img_out)
            if img_out is not None:
                yield img_out

    def enum_display_monitors(self):
        ''' Get positions of all monitors.

            If self.oneshot is True, this function has to return a dict
            with dimensions of all monitors at the same time.
            If the monitor has rotation, you have to deal with inside this method.

            Must returns a dict with a minima:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        '''
        pass

    def get_pixels(self, monitor_infos):
        ''' Retrieve screen pixels for a given monitor.

            monitor_infos should contain at least:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'heigth': the height
            }

            Returns a dict with pixels.

        '''
        pass


class MSSLinux(MSS):
    ''' Mutli-screen shot implementation for GNU/Linux.
        It uses intensively the Xlib.
    '''

    def __del__(self):
        ''' Disconnect from X server '''

        self.debug('__del__')

        if self.display:
            self.XCloseDisplay(self.display)

    def init(self):
        ''' GNU/Linux initialisations '''

        self.debug('init')

        x11 = find_library('X11')
        if x11 is None:
            raise OSError('MSSLinux: no X11 library found.')
        else:
            xlib = cdll.LoadLibrary(x11)

        self.debug('init', 'xlib', xlib)

        self.XOpenDisplay = xlib.XOpenDisplay
        self.XDefaultScreen = xlib.XDefaultScreen
        self.XDefaultRootWindow = xlib.XDefaultRootWindow
        self.XGetWindowAttributes = xlib.XGetWindowAttributes
        self.XAllPlanes = xlib.XAllPlanes
        self.XGetImage = xlib.XGetImage
        self.XGetPixel = xlib.XGetPixel
        self.XCreateImage = xlib.XCreateImage
        self.XFree = xlib.XFree
        self.XCloseDisplay = xlib.XCloseDisplay

        self._set_argtypes()
        self._set_restypes()

        display = None
        self.display = None
        try:
            display = environ[b'DISPLAY']
        except KeyError:
            err = 'MSSLinux: $DISPLAY not set. Stopping to prevent segfault.'
            raise ValueError(err)
        self.debug('init', '$DISPLAY', display)

        # At this point, if there is no running server, it could end on
        # a segmentation fault. And we cannot catch it.
        self.display = self.XOpenDisplay(display)
        self.debug('init', 'display', self.display)
        self.screen = self.XDefaultScreen(self.display)
        self.debug('init', 'screen', self.screen)
        self.root = self.XDefaultRootWindow(self.display, self.screen)
        self.debug('init', 'root', self.root)

    def _set_argtypes(self):
        ''' Functions arguments '''

        self.debug('_set_argtypes')

        self.XOpenDisplay.argtypes = [c_char_p]
        self.XDefaultScreen.argtypes = [POINTER(Display)]
        self.XDefaultRootWindow.argtypes = [POINTER(Display), c_int]
        self.XGetWindowAttributes.argtypes = [POINTER(Display),
            POINTER(XWindowAttributes), POINTER(XWindowAttributes)]
        self.XAllPlanes.argtypes = []
        self.XGetImage.argtypes = [POINTER(Display), POINTER(Display),
            c_int, c_int, c_uint, c_uint, c_ulong, c_int]
        self.XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        self.XCreateImage.argtypes = [POINTER(Display), POINTER(Display),
            c_int, c_int, c_uint, c_uint, c_ulong, c_int]
        self.XFree.argtypes = [POINTER(XImage)]
        self.XCloseDisplay.argtypes = [POINTER(Display)]

    def _set_restypes(self):
        ''' Functions return type '''

        self.debug('_set_restypes')

        self.XOpenDisplay.restype = POINTER(Display)
        self.XDefaultScreen.restype = c_int
        self.XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.XGetWindowAttributes.restype = c_int
        self.XAllPlanes.restype = c_ulong
        self.XGetImage.restype = POINTER(XImage)
        self.XGetPixel.restype = c_ulong
        self.XCreateImage.restype = POINTER(XImage)
        self.XFree.restype = c_void_p
        self.XCloseDisplay.restype = c_void_p

    def enum_display_monitors(self):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        self.debug('enum_display_monitors')

        results = []
        if self.oneshot:
            gwa = XWindowAttributes()
            self.XGetWindowAttributes(self.display, self.root, byref(gwa))
            results.append({
                b'left'  : int(gwa.x),
                b'top'   : int(gwa.y),
                b'width' : int(gwa.width),
                b'height': int(gwa.height)
            })
        else:
            # It is a little more complicated, we have to guess all stuff
            # from ~/.config/monitors.xml, if present.
            monitors = expanduser('~/.config/monitors.xml')
            if not isfile(monitors):
                self.debug('ERROR', 'MSSLinux: enum_display_monitors() failed (no monitors.xml).')
                self.oneshot = True
                return self.enum_display_monitors()
            tree = ET.parse(monitors)
            root = tree.getroot()
            config = root.findall('configuration')[-1]
            conf = []
            for output in config.findall('output'):
                name = output.get('name')
                if name != 'default':
                    x = output.find('x')
                    y = output.find('y')
                    width = output.find('width')
                    height = output.find('height')
                    rotation = output.find('rotation')
                    if None not in [x, y, width, height] and name not in conf:
                        conf.append(name)
                        if rotation.text == 'left' or rotation.text == 'right':
                            width, height = height, width
                        results.append({
                            b'left'    : int(x.text),
                            b'top'     : int(y.text),
                            b'width'   : int(width.text),
                            b'height'  : int(height.text),
                            b'rotation': rotation.text
                        })
        return results

    def get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB.
        '''

        self.debug('get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        ZPixmap = 2

        allplanes = self.XAllPlanes()
        self.debug('get_pixels', 'allplanes', allplanes)

        # Fix for XGetImage: expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        image = self.XGetImage(self.display, root, left, top, width,
            height, allplanes, ZPixmap)
        if image is None:
            raise ValueError('MSSLinux: XGetImage() failed.')

        pixels = [None] * (3 * width * height)
        for x in range(width):
            for y in range(height):
                pixel = self.XGetPixel(image, x, y)
                b = pixel & 255
                g = (pixel & 65280) >> 8
                r = (pixel & 16711680) >> 16
                offset = (x + width * y) * 3
                pixels[offset:offset+3] = pack(b'3B', r, g, b)
        self.XFree(image)
        return b''.join(pixels)


class MSSWindows(MSS):
    ''' Mutli-screen shot implementation for Microsoft Windows. '''

    def init(self):
        ''' Windows initialisations '''

        self.debug('init')

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

        self.debug('_set_argtypes')

        self.MONITORENUMPROC = WINFUNCTYPE(INT, DWORD, DWORD,
            POINTER(RECT), DOUBLE)
        self.GetSystemMetrics.argtypes = [INT]
        self.EnumDisplayMonitors.argtypes = [HDC, LPRECT,
            self.MONITORENUMPROC, LPARAM]
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

        self.debug('_set_restypes')

        self.GetSystemMetrics.restypes = INT
        self.EnumDisplayMonitors.restypes = BOOL
        self.GetWindowDC.restypes = HDC
        self.CreateCompatibleDC.restypes = HDC
        self.CreateCompatibleBitmap.restypes = HBITMAP
        self.SelectObject.restypes = HGDIOBJ
        self.BitBlt.restypes =  BOOL
        self.GetDIBits.restypes = INT
        self.DeleteObject.restypes = BOOL

    def enum_display_monitors(self):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        self.debug('enum_display_monitors')

        def _callback(monitor, dc, rect, data):
            rct = rect.contents
            results.append({
                b'left'  : int(rct.left),
                b'top'   : int(rct.top),
                b'width' : int(rct.right - rct.left),
                b'height': int(rct.bottom -rct.top)
            })
            return 1

        results = []
        if self.oneshot:
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            left = self.GetSystemMetrics(SM_XVIRTUALSCREEN)
            right = self.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            top = self.GetSystemMetrics(SM_YVIRTUALSCREEN)
            bottom = self.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            results.append({
                b'left'  : int(left),
                b'top'   : int(top),
                b'width' : int(right - left),
                b'height': int(bottom - top)
            })
        else:
            callback = self.MONITORENUMPROC(_callback)
            self.EnumDisplayMonitors(0, 0, callback, 0)
        return results

    def get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB. '''

        self.debug('get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        SRCCOPY = 0xCC0020
        DIB_RGB_COLORS = 0

        srcdc = self.GetWindowDC(0)
        memdc = self.CreateCompatibleDC(srcdc)
        bmp = self.CreateCompatibleBitmap(srcdc, width, height)
        self.SelectObject(memdc, bmp)
        self.BitBlt(memdc, 0, 0, width, height, srcdc, left, top, SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = height
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biPlanes = 1
        buffer_len = height * ((width * 3 + 3) & -4)
        pixels = create_string_buffer(buffer_len)
        bits = self.GetDIBits(memdc, bmp, 0, height, byref(pixels),
            pointer(bmi), DIB_RGB_COLORS)

        self.debug('get_pixels', 'srcdc', srcdc)
        self.debug('get_pixels', 'memdc', memdc)
        self.debug('get_pixels', 'bmp', bmp)
        self.debug('get_pixels', 'buffer_len', buffer_len)
        self.debug('get_pixels', 'bits', bits)
        self.debug('get_pixels', 'len(pixels.raw)', len(pixels.raw))

        # Clean up
        self.DeleteObject(srcdc)
        self.DeleteObject(memdc)
        self.DeleteObject(bmp)

        if bits != height or len(pixels.raw) != buffer_len:
            raise ValueError('MSSWindows: GetDIBits() failed.')

        # Note that the origin of the returned image is in the
        # bottom-left corner, 32-bit aligned. And it is BGR.
        # Need to "arrange" that.
        return self._arrange(pixels.raw, (width * 3 + 3) & -4, height)

    def _arrange(self, data, width, height):
        ''' Reorganises data when the origin of the image is in the
            bottom-left corner and converts BGR triple to RGB. '''

        total = width * height
        scanlines = [b'0'] * total
        for y in range(height):
            off = width * (y + 1)
            offset = total - off
            x = 0
            while x < width - 2:
                scanlines[off+x:off+x+3] = data[offset+x+2], data[offset+x+1], data[offset+x]
                x += 3
        return b''.join(scanlines)


class MSSImage(object):
    ''' This is a class to save data (raw pixels) to a picture file.
    '''

    # Known extensions
    ext_ok = [
        #'libjpg',  # ctypes over libjpeg
        'png',     # pure python PNG implementation
    ]

    def __init__(self, data=None, width=1, height=1):
        ''' This method is light and should not change. It is like this
            to allow the call of extensions() without manipulating
            real data.
        '''

        if width < 1 or height < 1:
            raise ValueError('MSSImage: width or height must be positive.')

        self.data = data
        self.width = int(width)
        self.height = int(height)

    def extensions(self):
        ''' List all known and working extensions. '''

        exts = []
        for ext in self.ext_ok:
            if hasattr(self, ext):
                exts.append(ext)
        return exts

    def dump(self, output=None, ext='png', quality=80, ftype=0):
        ''' Dump data to the image file using file format specified by ext.
            Returns to created file name if success, else None.
        '''

        if self.data is None:
            raise ValueError('MSSImage: no data to process.')

        self.filename = output
        self.ext = ext
        self.quality = max(0, min(int(quality), 100))
        self.filtertype = max(0, min(int(ftype), 4))
        contents = None

        if not hasattr(self, self.ext):
            err = 'MSSImage: {0}() not implemented. '.format(self.ext)
            err += 'Check MSSImage.extensions() to have more informations.'
            raise ValueError(err)

        contents = getattr(self, self.ext)()
        if contents is not None:
            self.filename += '.' + self.ext
            with open(self.filename, 'wb') as fileh:
                fileh.write(contents)
                return self.filename
        return None

    def libjpg(self):
        ''' JPEG implementation using ctypes over libjpeg.
        '''

        self.ext = 'jpg'
        print('ctypes over libjpeg still not implemented.')
        pass

    def png(self):
        ''' Pure python PNG implementation.
            Image represented as RGB tuples, no interlacing.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        self.ext = 'png'

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
                i = 0
                for x in line:
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
                    if pa <= pb and pa <= pc:
                        Pr = a
                    elif pb <= pc:
                        Pr = b
                    else:
                        Pr = c

                    x = (x - Pr) & 0xff
                    out += pack(b'B', x)
                    ai += 1
                    i += 1
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

        width, height, data = self.width, self.height, self.data

        to_take = (width * 3 + 3) & -4
        padding = 0 if to_take % 8 == 0 else (to_take % 8) // 2
        offset = 0
        scanlines = b''
        prev = None
        for y in range(height):
            line = bytearray(data[offset:offset+to_take-padding])
            scanlines += filter_scanline(self.filtertype, line, 3, prev)
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


if __name__ == '__main__':

    this_is = system()
    if this_is == 'Linux':
        MSS = MSSLinux
    elif this_is == 'Windows':
        MSS = MSSWindows
    else:
        err = 'System "{0}" not implemented.'.format(this_is)
        raise NotImplementedError(err)

    try:
        mss = MSS(debug=False)

        # One screen shot per monitor
        for filename in mss.save():
            print('File "{0}" created.'.format(filename))

        # A shot to grab them all :)
        for filename in mss.save(oneshot=True):
            print('File "{0}" created.'.format(filename))
    except Exception as ex:
        print(ex)
        raise
