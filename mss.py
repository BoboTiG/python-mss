#!/usr/bin/env python
# -*- coding: utf-8 -*-

''' A cross-platform multi-screen shot module in pure python using ctypes.

    This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

    Note: please keep this module compatible to Python 2.6.

    You can always get the latest version of this module at:
        https://raw.github.com/BoboTiG/python-mss/master/mss.py
    If that URL should fail, try contacting the author.
'''

from __future__ import (unicode_literals, absolute_import,
                        division, print_function)

__version__ = '0.0.7'
__author__ = "Mickaël 'Tiger-222' Schoentgen"
__copyright__ = '''
    Copyright (c) 2013-2014, Mickaël 'Tiger-222' Schoentgen

    Permission to use, copy, modify, and distribute this software and its
    documentation for any purpose and without fee or royalty is hereby
    granted, provided that the above copyright notice appear in all copies
    and that both that copyright notice and this permission notice appear
    in supporting documentation or portions thereof, including
    modifications, that you make.
'''
__all__ = ['MSSLinux', 'MSSMac', 'MSSWindows']


from struct import pack
from platform import system
import os.path
import sys
import zlib


class ScreenshotError(Exception):
    ''' Error handling class. '''
    pass

if system() == 'Darwin':
    from Quartz import *
    from LaunchServices import kUTTypePNG
elif system() == 'Linux':
    from os import environ
    from os.path import expanduser
    import xml.etree.ElementTree as ET
    from ctypes.util import find_library
    from ctypes import byref, cast, cdll, POINTER, Structure, \
        c_char_p, c_int, c_int32, c_uint, c_uint32, c_ulong, c_void_p

    class Display(Structure):
        pass

    class XWindowAttributes(Structure):
        _fields_ = [
            ('x',                     c_int32),
            ('y',                     c_int32),
            ('width',                 c_int32),
            ('height',                c_int32),
            ('border_width',          c_int32),
            ('depth',                 c_int32),
            ('visual',                c_ulong),
            ('root',                  c_ulong),
            ('class',                 c_int32),
            ('bit_gravity',           c_int32),
            ('win_gravity',           c_int32),
            ('backing_store',         c_int32),
            ('backing_planes',        c_ulong),
            ('backing_pixel',         c_ulong),
            ('save_under',            c_int32),
            ('colourmap',             c_ulong),
            ('mapinstalled',          c_uint32),
            ('map_state',             c_uint32),
            ('all_event_masks',       c_ulong),
            ('your_event_mask',       c_ulong),
            ('do_not_propagate_mask', c_ulong),
            ('override_redirect',     c_int32),
            ('screen',                c_ulong)
            ]

    class XImage(Structure):
        _fields_ = [
            ('width',             c_int),
            ('height',            c_int),
            ('xoffset',           c_int),
            ('format',            c_int),
            ('data',              c_char_p),
            ('byte_order',        c_int),
            ('bitmap_unit',       c_int),
            ('bitmap_bit_order',  c_int),
            ('bitmap_pad',        c_int),
            ('depth',             c_int),
            ('bytes_per_line',    c_int),
            ('bits_per_pixel',    c_int),
            ('red_mask',          c_ulong),
            ('green_mask',        c_ulong),
            ('blue_mask',         c_ulong)
            ]

    def b(x):
        return pack(b'<B', x)
elif system() == 'Windows':
    from ctypes import byref, c_void_p, create_string_buffer, pointer, \
        sizeof, windll, Structure, POINTER, WINFUNCTYPE
    from ctypes.wintypes import BOOL, DOUBLE, DWORD, HBITMAP, HDC, \
        HGDIOBJ, HWND, INT, LPARAM, LONG, RECT, UINT, WORD

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

    if sys.version < '3':
        def b(x):
            return x
    else:
        def b(x):
            return pack(b'<B', x)
else:
    raise ScreenshotError('System "{}" not implemented.'.format(system()))


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

        self.DEBUG = debug in [True, 'on' 'yes', 'oui', 1]
        self.debug('__init__', 'DEBUG', self.DEBUG)
        self.init()

    def debug(self, method='', scalar=None, value=None):
        ''' Simple debug output. '''

        if self.DEBUG:
            if scalar is None:
                print(':: {}()'.format(method))
            else:
                print('{}() {} {} {}'.format(method, scalar,
                                             type(value).__name__,
                                             value))

    def enum_display_monitors(self):
        ''' Get positions of all monitors.

            If self.oneshot is True, this function has to return a dict
            with dimensions of all monitors at the same time.
            If the monitor has rotation, you have to deal with inside
            this method.

            Must returns a dict with a minima:
            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }
        '''
        return NotImplemented

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
        return NotImplemented

    def save(self,
             output='screenshot-%d.png',
             screen=0,
             callback=lambda *x: True
             ):
        ''' For each monitor, grab a screen shot and save it to a file.

            Parameters:
             - output - string - the output filename. It can contain '%d' which
                                 will be replaced by the monitor number.
             - screen - int - grab one screen shot of all monitors (screen=-1)
                              grab one screen shot by monitor (screen=0)
                              grab the screen shot of the monitor N (screen=N)
             - callback - function - in case where output already exists, call
                                     the defined callback function with output
                                     as parameter. If it returns True, then
                                     continue; else ignores the monitor and
                                     switches to ne next.

            This is a generator which returns created files.
        '''

        self.debug('save')
        self.debug('save', 'screen', screen)
        self.debug('save', 'output', output)

        # Monitors screen shots!
        dir_ = os.getcwd()
        for i, monitor in enumerate(self.enum_display_monitors(screen)):
            self.debug('save', 'monitor', monitor)
            if screen <= 0 or (screen > 0 and i+1 == screen):
                fname = output
                if '%d' in output:
                    fname = output.replace('%d', str(i+1))
                fname = os.path.join(dir_, os.path.basename(fname))
                self.debug('save', 'fname', fname)
                if os.path.isfile(fname) and not callback(fname):
                    continue
                self.save_img(data=self.get_pixels(monitor),
                              width=monitor[b'width'],
                              height=monitor[b'height'],
                              output=fname)
                yield fname

    def save_img(self, data, width, height, output):
        ''' Dump data to the image file.
            Pure python PNG implementation.
            Image represented as RGB tuples, no interlacing.
            http://inaps.org/journal/comment-fonctionne-le-png
        '''

        self.debug('save_img')

        to_take = (width * 3 + 3) & -4
        padding = 0 if to_take % 8 == 0 else (to_take % 8) // 2
        scanlines = b''.join(
            [b'0' + data[(y*to_take):(y*to_take)+to_take-padding]
             for y in range(height)]
            )

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

        with open(output, 'wb') as fileh:
            fileh.write(
                magic + b''.join(ihdr) + b''.join(idat) + b''.join(iend)
                )
        if not os.path.isfile(output):
            msg = 'Impossible to write data to file "{}".'.format(output)
            raise ScreenshotError(msg)


class MSSMac(MSS):
    ''' Mutli-screen shot implementation for Mac OSX.
        It uses intensively the Quartz.
    '''

    def init(self):
        ''' Mac OSX initialisations '''
        self.debug('init')

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        self.debug('enum_display_monitors')

        if screen == -1:
            rect = CGRectInfinite
            yield ({
                b'left': int(rect.origin.x),
                b'top': int(rect.origin.y),
                b'width': int(rect.size.width),
                b'height': int(rect.size.height)
                })
        else:
            max_displays = 32  # Could be augmented, if needed ...
            rotations = {0.0: 'normal', 90.0: 'right', -90.0: 'left'}
            _, ids, _ = CGGetActiveDisplayList(max_displays, None, None)
            for display in ids:
                rect = CGRectStandardize(CGDisplayBounds(display))
                left, top = rect.origin.x, rect.origin.y
                width, height = rect.size.width, rect.size.height
                rot = CGDisplayRotation(display)
                rotation = rotations[rot]
                if rotation in ['left', 'right']:
                    width, height = height, width
                yield ({
                    b'left': int(left),
                    b'top': int(top),
                    b'width': int(width),
                    b'height': int(height),
                    b'rotation': rotation
                    })

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB.
        '''

        self.debug('get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        rect = CGRect((left, top), (width, height))
        image = CGWindowListCreateImage(
            rect, kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID, kCGWindowImageDefault)
        if not image:
            raise ScreenshotError('CGWindowListCreateImage() failed.')
        return image

    def save_img(self, data, width, height, output):
        ''' Use my own save_img() method. Because I'm Mac! '''

        self.debug('MSSMac: save_img')

        url = NSURL.fileURLWithPath_(output)
        dest = CGImageDestinationCreateWithURL(url, kUTTypePNG, 1, None)
        if not dest:
            msg = 'Error while trying to create the image destination ' \
                  'to "{}".'.format(output)
            raise ScreenshotError(msg)
        CGImageDestinationAddImage(dest, data, None)
        if not CGImageDestinationFinalize(dest):
            msg = 'Impossible to write data to file "{}".'.format(output)
            raise ScreenshotError(msg)


class MSSLinux(MSS):
    ''' Mutli-screen shot implementation for GNU/Linux.
        It uses intensively the Xlib.
    '''

    def __del__(self):
        ''' Disconnect from X server '''

        self.debug('__del__')

        if self.display:
            self.xlib.XCloseDisplay(self.display)

    def init(self):
        ''' GNU/Linux initialisations '''

        self.debug('init')

        x11 = find_library('X11')
        if not x11:
            raise ScreenshotError('No X11 library found.')

        self.xlib = cdll.LoadLibrary(x11)
        self.debug('init', 'xlib', self.xlib)

        self._set_argtypes()
        self._set_restypes()

        disp = None
        self.display = None
        try:
            if sys.version > '3':
                disp = bytes(environ['DISPLAY'], 'utf-8')
            else:
                disp = environ['DISPLAY']
        except KeyError:
            err = '$DISPLAY not set. Stopping to prevent segfault.'
            raise ScreenshotError(err)
        self.debug('init', '$DISPLAY', disp)

        # At this point, if there is no running server, it could end on
        # a segmentation fault. And we cannot catch it.
        self.display = self.xlib.XOpenDisplay(disp)
        self.debug('init', 'display', self.display)
        self.screen = self.xlib.XDefaultScreen(self.display)
        self.debug('init', 'screen', self.screen)
        self.root = self.xlib.XDefaultRootWindow(self.display, self.screen)
        self.debug('init', 'root', self.root)

    def _set_argtypes(self):
        ''' Functions arguments '''

        self.debug('_set_argtypes')

        self.xlib.XOpenDisplay.argtypes = [c_char_p]
        self.xlib.XDefaultScreen.argtypes = [POINTER(Display)]
        self.xlib.XDefaultRootWindow.argtypes = [POINTER(Display), c_int]
        self.xlib.XGetWindowAttributes.argtypes = [POINTER(Display),
                                                   POINTER(XWindowAttributes),
                                                   POINTER(XWindowAttributes)]
        self.xlib.XAllPlanes.argtypes = []
        self.xlib.XGetImage.argtypes = [POINTER(Display), POINTER(Display),
                                        c_int, c_int, c_uint, c_uint,
                                        c_ulong, c_int]
        self.xlib.XGetPixel.argtypes = [POINTER(XImage), c_int, c_int]
        self.xlib.XFree.argtypes = [POINTER(XImage)]
        self.xlib.XCloseDisplay.argtypes = [POINTER(Display)]

    def _set_restypes(self):
        ''' Functions return type '''

        self.debug('_set_restypes')

        self.xlib.XOpenDisplay.restype = POINTER(Display)
        self.xlib.XDefaultScreen.restype = c_int
        self.xlib.XDefaultRootWindow.restype = POINTER(XWindowAttributes)
        self.xlib.XGetWindowAttributes.restype = c_int
        self.xlib.XAllPlanes.restype = c_ulong
        self.xlib.XGetImage.restype = POINTER(XImage)
        self.xlib.XGetPixel.restype = c_ulong
        self.xlib.XFree.restype = c_void_p
        self.xlib.XCloseDisplay.restype = c_void_p

    def _x11_config(self):
        ''' Try to determine display monitors from X11 configuration file:
            ~/.config/monitors.xml
        '''

        self.debug('_x11_config')

        monitors = expanduser('~/.config/monitors.xml')
        if not os.path.isfile(monitors):
            self.debug('ERROR', 'MSSLinux: _x11_config() failed.')
            return

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
                    if rotation.text in ['left', 'right']:
                        width, height = height, width
                    yield ({
                        b'left': int(x.text),
                        b'top': int(y.text),
                        b'width': int(width.text),
                        b'height': int(height.text),
                        b'rotation': rotation.text
                        })

    def _xfce4_config(self):
        ''' Try to determine display monitors from XFCE4 configuration file:
            ~/.config/xfce4/xfconf/xfce-perchannel-xml/displays.xml
        '''

        self.debug('_xfce4_config')

        path_ = '~/.config/xfce4/xfconf/xfce-perchannel-xml/displays.xml'
        monitors = expanduser(path_)
        if not os.path.isfile(monitors):
            self.debug('ERROR', 'MSSLinux: _xfce4_config() failed.')
            return

        rotations = {0: 'normal', 90: 'left', 270: 'right'}
        tree = ET.parse(monitors)
        root = tree.getroot()
        config = root.findall('property')[0]
        for output in config.findall('property'):
            name = output.get('name')
            if name != 'default':
                active, res, _, rot, _, _, pos = output.findall('property')
                if active.get('value') == 'true':
                    width, height = res.get('value').split('x')
                    rotation = rotations[int(rot.get('value'))]
                    if rotation in ['left', 'right']:
                        width, height = height, width
                    posx, posy = pos.findall('property')
                    yield ({
                        b'left': int(posx.get('value')),
                        b'top': int(posy.get('value')),
                        b'width': int(width),
                        b'height': int(height),
                        b'rotation': rotation
                        })

    def enum_display_monitors(self, screen=0):
        ''' Get positions of one or more monitors.
            Returns a dict with minimal requirements (see MSS class).
        '''

        self.debug('enum_display_monitors')

        if screen == -1:
            gwa = XWindowAttributes()
            self.xlib.XGetWindowAttributes(self.display, self.root, byref(gwa))
            yield ({
                b'left': int(gwa.x),
                b'top': int(gwa.y),
                b'width': int(gwa.width),
                b'height': int(gwa.height)
                })
        else:
            # It is a little more complicated, we have to guess all stuff
            # from differents XML configuration files.
            for config in ['x11', 'xfce4']:
                for mon in getattr(self, '_{}_config'.format(config))():
                    if mon:
                        yield mon

    def get_pixels(self, monitor):
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB.
        '''

        self.debug('get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        ZPixmap = 2

        allplanes = self.xlib.XAllPlanes()
        self.debug('get_pixels', 'allplanes', allplanes)

        # Fix for XGetImage:
        # expected LP_Display instance instead of LP_XWindowAttributes
        root = cast(self.root, POINTER(Display))

        ximage = self.xlib.XGetImage(self.display, root, left, top, width,
                                     height, allplanes, ZPixmap)
        if not ximage:
            raise ScreenshotError('XGetImage() failed.')

        def pix(pixel, _resultats={}):
            ''' Apply shifts to a pixel to get the RGB values.
                This method uses of memoization.
            '''
            if not pixel in _resultats:
                _resultats[pixel] = b((pixel & 16711680) >> 16) + \
                    b((pixel & 65280) >> 8) + b(pixel & 255)
            return _resultats[pixel]

        # http://cgit.freedesktop.org/xorg/lib/libX11/tree/src/ImUtil.c#n444
        get_pix = self.xlib.XGetPixel
        pixels = [pix(get_pix(ximage, x, y))
                  for y in range(height) for x in range(width)]

        self.xlib.XFree(ximage)
        image = b''.join(pixels)
        return image


class MSSWindows(MSS):
    ''' Mutli-screen shot implementation for Microsoft Windows. '''

    def init(self):
        ''' Windows initialisations '''

        self.debug('init')

        self._set_argtypes()
        self._set_restypes()

    def _set_argtypes(self):
        ''' Functions arguments '''

        self.debug('_set_argtypes')

        self.MONITORENUMPROC = WINFUNCTYPE(INT, DWORD, DWORD,
                                           POINTER(RECT), DOUBLE)
        windll.user32.GetSystemMetrics.argtypes = [INT]
        windll.user32.EnumDisplayMonitors.argtypes = [HDC, c_void_p,
                                                      self.MONITORENUMPROC,
                                                      LPARAM]
        windll.user32.GetWindowDC.argtypes = [HWND]
        windll.gdi32.CreateCompatibleDC.argtypes = [HDC]
        windll.gdi32.CreateCompatibleBitmap.argtypes = [HDC, INT, INT]
        windll.gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
        windll.gdi32.BitBlt.argtypes = [HDC, INT, INT, INT, INT, HDC,
                                        INT, INT, DWORD]
        windll.gdi32.DeleteObject.argtypes = [HGDIOBJ]
        windll.gdi32.GetDIBits.argtypes = [HDC, HBITMAP, UINT, UINT, c_void_p,
                                           POINTER(BITMAPINFO), UINT]

    def _set_restypes(self):
        ''' Functions return type '''

        self.debug('_set_restypes')

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

        self.debug('enum_display_monitors')

        if screen == -1:
            SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 76, 77
            SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 78, 79
            left = windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            right = windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            top = windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            bottom = windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            yield ({
                b'left': int(left),
                b'top': int(top),
                b'width': int(right - left),
                b'height': int(bottom - top)
                })
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
        ''' Retrieve all pixels from a monitor. Pixels have to be RGB. '''

        self.debug('get_pixels')

        width, height = monitor[b'width'], monitor[b'height']
        left, top = monitor[b'left'], monitor[b'top']
        good_width = (width * 3 + 3) & -4
        SRCCOPY = 0xCC0020
        DIB_RGB_COLORS = 0

        srcdc = windll.user32.GetWindowDC(0)
        memdc = windll.gdi32.CreateCompatibleDC(srcdc)
        bmp = windll.gdi32.CreateCompatibleBitmap(srcdc, width, height)
        windll.gdi32.SelectObject(memdc, bmp)
        windll.gdi32.BitBlt(memdc, 0, 0, width, height, srcdc, left,
                            top, SRCCOPY)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = height
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biPlanes = 1
        buffer_len = height * good_width
        pixels = create_string_buffer(buffer_len)
        bits = windll.gdi32.GetDIBits(memdc, bmp, 0, height, byref(pixels),
                                      pointer(bmi), DIB_RGB_COLORS)

        self.debug('get_pixels', 'srcdc', srcdc)
        self.debug('get_pixels', 'memdc', memdc)
        self.debug('get_pixels', 'bmp', bmp)
        self.debug('get_pixels', 'buffer_len', buffer_len)
        self.debug('get_pixels', 'bits', bits)
        self.debug('get_pixels', 'len(pixels.raw)', len(pixels.raw))

        # Clean up
        windll.gdi32.DeleteObject(srcdc)
        windll.gdi32.DeleteObject(memdc)
        windll.gdi32.DeleteObject(bmp)

        if bits != height or len(pixels.raw) != buffer_len:
            raise ScreenshotError('GetDIBits() failed.')

        # Note that the origin of the returned image is in the
        # bottom-left corner, 32-bit aligned. And it is BGR.
        # Need to "arrange" that.
        return self._arrange(pixels.raw, good_width, height)

    def _arrange(self, data, width, height):
        ''' Reorganises data when the origin of the image is in the
            bottom-left corner and converts BGR triple to RGB. '''

        self.debug('_arrange')

        total = width * height
        scanlines = [b'0'] * total
        for y in range(height):
            off = width * (y + 1)
            offset = total - off
            for x in range(0, width - 2, 3):
                scanlines[off+x:off+x+3] = \
                    b(data[offset+x+2]), b(data[offset+x+1]), b(data[offset+x])
        image = b''.join(scanlines)
        return image


def main(argv=[]):
    ''' Usage example. '''

    from contextlib import contextmanager
    from time import time

    @contextmanager
    def timer(msg):
        ''' A little timer '''
        start = time()
        yield
        end = time()
        print('{}: {} ms'.format(msg, (end-start)*1000))

    systems = {
        'Darwin': MSSMac,
        'Linux': MSSLinux,
        'Windows': MSSWindows
        }
    mss = systems[system()](debug='--debug' in argv)

    try:
        # One screen shot per monitor
        with timer('Screen shots'):
            for filename in mss.save():
                print('        File: {}'.format(filename))

        # Screen shot of the monitor 1
        with timer('Monitor 1   '):
            for filename in mss.save(output='monitor-%d.png', screen=1):
                print('        File: {}'.format(filename))

        # A shot to grab them all :)
        with timer('All in one  '):
            for filename in mss.save(output='full-screenshot.png', screen=-1):
                print('        File: {}'.format(filename))

        # Example with a callback
        def on_exists(fname):
            ''' Callback example when we try to overwrite an existing
                screen shot.
            '''
            from os import rename
            newfile = fname + '.old'
            print('        Renaming {} to {}'.format(fname, newfile))
            rename(fname, newfile)
            return True

        # Screen shot of the monitor 1, with callback
        with timer('Monitor 1   '):
            for fname in mss.save(output='mon-%d.png',
                                  screen=1, callback=on_exists):
                print('        File: {}'.format(fname))
    except ScreenshotError as ex:
        print(ex)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
