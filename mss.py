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
__all__ = ['bgr_to_rgb', 'MSS', 'MSSImage']


from ctypes.util import find_library
from struct import calcsize, pack
from os.path import isfile
import zlib
from platform import system

if system() == 'Windows':
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
                ('biSize', DWORD),
                ('biWidth', LONG),
                ('biHeight', LONG),
                ('biPlanes', WORD),
                ('biBitCount', WORD),
                ('biCompression', DWORD),
                ('biSizeImage', DWORD),
                ('biXPelsPerMeter', LONG),
                ('biYPelsPerMeter', LONG),
                ('biClrUsed', DWORD),
                ('biClrImportant', DWORD)
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

    def __init__(self):
        ''' Global vars and class overload. '''

        self.monitors = ()
        self.oneshot = False

        this_is = system()
        if this_is == 'Windows':
            self.__class__ = MSSWindows
        else:
            err = 'System "{0}" not implemented.'.format(this_is)
            raise NotImplementedError(err)
        
        self.init()

    def save(self, output='mss', oneshot=False, ext='jpg'):
        ''' For each monitor, grab a screen shot and save it to a file.

            Parameters:
             - output - string - the output filename without extension
             - oneshot - c_longean -grab only one screen shot of all monitors
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
        self.monitors = self._enum_display_monitors()

        if len(self.monitors) < 1:
            raise ValueError('MSS: no monitor found.')

        # Monitors screen shots!
        i = 1
        for monitor in self.monitors:
            if self.oneshot:
                filename = output + '-full'
            else:
                filename = output + '-' + str(i)
                i += 1
            monitor['width'] = monitor['right'] - monitor['left']
            monitor['height'] = monitor['bottom'] - monitor['top']
            pixels = self._get_pixels(monitor)
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


class MSSWindows(MSS):
    ''' Mutli-screen shot implementation for Microsoft Windows. '''

    def init(self):
        ''' Windows related ctypes imports '''
        
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

    def dump(self, output=None, ext='jpg', quality=80):
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
        if quality < 1:
            raise ValueError('MSSImage: quality must be positive.')

        self.filename = output
        self.ext = ext
        self.quality = min(quality, 100)
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
                img = Image.frombuffer('RGB', (self.width, self.height),
                                        self.data, 'raw', 'RGB', buffer_len, 1)
                ImageFile.MAXBLOCK = self.width * self.height
                #img.save(tmp, quality=self.quality, optimize=True, progressive=True)
                img.save(tmp, quality=self.quality)
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

        self.ext = 'png'
        width, height, data = self.width, self.height, self.data
        
        to_take = (width * 3 + 3) & -4
        offset = 0
        scanlines = b''
        for y in range(height):
            scanlines += b'\0' + data[offset:offset + to_take]
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
        #idat[2] = scanlines
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
        for filename in mss.save():
            print('File "{0}" created.'.format(filename))
        for filename in mss.save(ext='libpng'):
            print('File "{0}" created.'.format(filename))

        # A screen shot to grab them all :)
        #for filename in mss.save(oneshot=True):
        #    print('File "{0}" created.'.format(filename))
    except Exception as ex:
        print(ex)
        #raise
        
    '''
    # MSSImage tests
    try:
        img = MSSImage()

        img.width = 1440
        img.height = 900
        with open('data.raw', 'rb') as fileh:
            data = fileh.read()
            
            img.data = data
            img.dump('data-output-pil', ext='png', quality=100)
            print('File "{0}" created.'.format(img.output))
            
            img.data = data
            img.dump('data-output', ext='libpng')
            print('File "{0}" created.'.format(img.output))
        
        print("")
        
        img.width = 1366
        img.height = 768
        with open('data2.raw', 'rb') as fileh:
            data = fileh.read()
            
            img.data = data
            img.dump('data2-output-pil', ext='png', quality=100)
            print('File "{0}" created.'.format(img.output))
            
            img.data = data
            img.dump('data2-output', ext='libpng')
            print('File "{0}" created.'.format(img.output))
    except Exception as ex:
        print(ex)
        raise
    '''
