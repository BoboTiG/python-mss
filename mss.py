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
__all__ = ['MSSLinux', 'MSSWindows', 'MSSImage']


from ctypes.util import find_library
from struct import pack
import zlib
from platform import system

if system() == 'Linux':
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

    def debug(self, method='', scalar='', value=None):
        ''' Simple debug output. '''

        if self.DEBUG:
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

        self.oneshot = oneshot
        self.monitors = self._enum_display_monitors() or []

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
            monitor[b'width'] = monitor[b'right'] - monitor[b'left']
            monitor[b'height'] = monitor[b'bottom'] - monitor[b'top']
            try:
                if monitor[b'rotation'] == 'left' or monitor[b'rotation'] == 'right':
                    monitor[b'width'] = monitor[b'bottom']
                    monitor[b'height'] = monitor[b'right'] - monitor[b'top']
            except KeyError:
                pass

            pixels = self._get_pixels(monitor)
            if pixels is None:
                raise ValueError('MSS: no data to process.')

            img = MSSImage(pixels, monitor[b'width'], monitor[b'height'])
            img_out = img.dump(filename, ext=ext, ftype=ftype)
            self.debug('save', 'img_out', img_out)
            if img_out is not None:
                yield img_out

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

        self.debug('init', 'xlib', xlib)

        self.XOpenDisplay = xlib.XOpenDisplay
        self.XDefaultRootWindow = xlib.XDefaultRootWindow
        self.XGetWindowAttributes = xlib.XGetWindowAttributes
        self.XAllPlanes = xlib.XAllPlanes
        self.XGetImage = xlib.XGetImage
        self.XGetPixel = xlib.XGetPixel
        self.XCreateImage = xlib.XCreateImage
        self.XFree = xlib.XFree

        self._set_argtypes()
        self._set_restypes()

        # Constants and scalars
        self.ZPixmap = 2
        self.display = self.XOpenDisplay(None)
        self.debug('init', 'display', self.display)
        self.root = self.XDefaultRootWindow(self.display)
        self.debug('init', 'root', self.root)

    def _set_argtypes(self):
        ''' Functions arguments '''
        
        self.debug('_set_argtypes', 'Functions arguments')

        self.XOpenDisplay.argtypes = [c_char_p]
        self.XDefaultRootWindow.argtypes = [POINTER(Display)]
        self.XGetWindowAttributes.argtypes = [POINTER(Display),
            POINTER(XWindowAttributes), POINTER(XWindowAttributes)]
        self.XAllPlanes.argtypes = []
        self.XGetImage.argtypes = [POINTER(Display), POINTER(Display),
            c_int, c_int, c_uint, c_uint, c_ulong, c_int]
        self.XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        self.XCreateImage.argtypes = [POINTER(Display), POINTER(Display),
            c_int, c_int, c_uint, c_uint, c_ulong, c_int]
        self.XFree.argtypes = [POINTER(XImage)]

    def _set_restypes(self):
        ''' Functions return type '''
        
        self.debug('_set_restypes', 'Functions return type')

        self.XOpenDisplay.restype = POINTER(Display)
        self.XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.XGetWindowAttributes.restype = c_int
        self.XAllPlanes.restype = c_ulong
        self.XGetImage.restype = POINTER(XImage)
        self.XGetPixel.restype = c_ulong
        self.XCreateImage.restype = POINTER(XImage)
        self.XFree.restype = c_void_p

    def _enum_display_monitors(self):
        '''
            Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''
        
        self.debug('_enum_display_monitors', '_enum_display_monitors')

        results = []
        if self.oneshot:
            gwa = XWindowAttributes()
            self.XGetWindowAttributes(self.display, self.root, byref(gwa))
            infos = {b'left': gwa.x, b'right': gwa.width,
                    b'top': gwa.y, b'bottom': gwa.height}
            results.append(infos)
        else:
            # It is a little more complicated, we have to guess all stuff
            # from ~/.config/monitors.xml, if present.
            monitors = expanduser('~/.config/monitors.xml')
            if not isfile(monitors):
                raise ValueError('MSSLinux: _enum_display_monitors() failed (no monitors.xml).')
            tree = ET.parse(monitors)
            root = tree.getroot()
            for config in root.findall('configuration'):
                if config.find('clone').text == 'no':
                    for output in config.findall('output'):
                        if output.get('name') != 'default':
                            x = output.find('x')
                            y = output.find('y')
                            width = output.find('width')
                            height = output.find('height')
                            rotation = output.find('rotation')
                            if None not in [x, y, width, height]:
                                results.append({
                                    b'left'    : int(x.text),
                                    b'right'   : int(width.text),
                                    b'top'     : int(y.text),
                                    b'bottom'  : int(height.text),
                                    b'rotation': rotation.text
                                })
        return results

    def _get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB.
        '''
        
        self.debug('_get_pixels', '_get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']

        allplanes = self.XAllPlanes()
        self.debug('_get_pixels', 'allplanes', allplanes)

        # Fix for XGetImage: expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        image = self.XGetImage(self.display, root, left, top, width,
            height, allplanes, self.ZPixmap)
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

        self.debug('init', 'initialisations')

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
        
        self.debug('_set_argtypes', 'Functions arguments')

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
        
        self.debug('_set_restypes', 'Functions return type')

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
        
        self.debug('_enum_display_monitors', '_enum_display_monitors')

        def _callback(monitor, dc, rect, data):
            rct = rect.contents
            infos = {b'left': int(rct.left), b'right': int(rct.right),
                    b'top': int(rct.top), b'bottom': int(rct.bottom)}
            results.append(infos)
            return 1

        results = []
        if self.oneshot:
            left = self.GetSystemMetrics(self.SM_XVIRTUALSCREEN)
            right = self.GetSystemMetrics(self.SM_CXVIRTUALSCREEN)
            top = self.GetSystemMetrics(self.SM_YVIRTUALSCREEN)
            bottom = self.GetSystemMetrics(self.SM_CYVIRTUALSCREEN)
            results.append({b'left': int(left), b'right': int(right),
                            b'top': int(top), b'bottom': int(bottom)})
        else:
            callback = self.MONITORENUMPROC(_callback)
            self.EnumDisplayMonitors(0, 0, callback, 0)
        return results

    def _get_pixels(self, monitor):
        ''' Retreive all pixels from a monitor. Pixels have to be RGB. '''
        
        self.debug('_get_pixels', '_get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']

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

        return bottom_left(pixels.raw, width, height)
        return pixels.raw

        # Note that the origin of the returned image is in the
        # bottom-left corner, 32-bit aligned. Need to "arrange" that.
        data = bottom_left(pixels.raw, width, height)
        return bgr_to_rgb(data, width, height)


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
        self.width = width
        self.height = height

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
        self.quality = max(0, min(quality, 100))
        self.filtertype = max(0, min(ftype, 4))
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
        '''
            JPEG implementation using ctypes over libjpeg.
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


def bottom_left(data, width, height):
    ''' Reorganise data when the origin of the image is in the
        bottom-left corner. '''

    scanlines = b''
    y = height - 1
    while y >= 0:
        offstart = y * width * 3
        offend = ((y + 1) * width * 3)
        scanlines += data[offstart:offend]
        y -= 1
    return scanlines
    '''scanlines = b''
    y = height - 1
    while y >= 0:
        offstart = (y * width * 3 + 3) & -4
        offend = ((y + 1) * width * 3 + 3) & -4
        scanlines += data[offstart:offend]
        y -= 1
    return scanlines'''


def bgr_to_rgb(data, width, height):
    ''' Convert BGR triple to RGB. '''

    rgb = [None] * (3 * width * height)
    for x in range(width):
        for y in range(height):
            off = 3 * (width * y + x)
            rgb[off:off+3] = pack(b'3B', data[off+2], data[off+1], data[off])
    return rgb


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
        mss = MSS(debug=True)

        # One screen shot per monitor
        for filename in mss.save():
            print('File "{0}" created.'.format(filename))

        # A shot to grab them all :)
        for filename in mss.save(oneshot=True):
            print('File "{0}" created.'.format(filename))
    except Exception as ex:
        print(ex)
        raise
