#!/usr/bin/env python
# coding: utf-8
''' MacOS X version of the MSS module. See __init__.py. '''

from __future__ import absolute_import

from LaunchServices import kUTTypePNG
from Quartz import (
    NSURL, CGDisplayBounds, CGDisplayRotation, CGGetActiveDisplayList,
    CGImageDestinationAddImage, CGImageDestinationCreateWithURL,
    CGImageDestinationFinalize, CGRect, CGRectInfinite, CGRectStandardize,
    CGWindowListCreateImage, kCGNullWindowID, kCGWindowImageDefault,
    kCGWindowListOptionOnScreenOnly)

from .helpers import MSS, ScreenshotError

__all__ = ['MSSMac']


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
            raise ScreenshotError('CGWindowListCreateImage() failed.')
        return self.image

    def to_png(self, data, width, height, output):
        ''' Use of internal tools, faster and less code to write :) '''

        url = NSURL.fileURLWithPath_(output)
        dest = CGImageDestinationCreateWithURL(url, kUTTypePNG, 1, None)
        if not dest:
            err = 'CGImageDestinationCreateWithURL() failed.'
            raise ScreenshotError(err)

        CGImageDestinationAddImage(dest, data, None)
        if CGImageDestinationFinalize(dest):
            return True
        raise ScreenshotError('CGImageDestinationFinalize() failed.')
