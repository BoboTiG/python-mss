#!/usr/bin/env python
# coding: utf-8
''' This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
'''

# pylint: disable=import-error

from Quartz import (
    NSURL, CGDisplayBounds, CGDisplayRotation, CGGetActiveDisplayList,
    CGImageDestinationAddImage, CGImageDestinationCreateWithURL,
    CGImageDestinationFinalize, CGRect, CGRectInfinite, CGRectStandardize,
    CGWindowListCreateImage, kCGNullWindowID, kCGWindowImageDefault,
    kCGWindowListOptionOnScreenOnly)

from .base import MSSBase
from .exception import ScreenshotError

__all__ = ['MSS']


class MSS(MSSBase):
    ''' Mutliple ScreenShots implementation for MacOS X.
        It uses intensively the Quartz.
    '''

    def enum_display_monitors(self, force=False):
        ''' Get positions of monitors (see parent class). '''

        if not self.monitors or force:
            # All monitors
            rect = CGRectInfinite
            self.monitors.append({
                b'left': int(rect.origin.x),
                b'top': int(rect.origin.y),
                b'width': int(rect.size.width),
                b'height': int(rect.size.height)
            })

            # Each monitors
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
                self.monitors.append({
                    b'left': int(left),
                    b'top': int(top),
                    b'width': int(width),
                    b'height': int(height)
                })

        return self.monitors

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
        dest = CGImageDestinationCreateWithURL(url, 'public.png', 1, None)
        if not dest:
            err = 'CGImageDestinationCreateWithURL() failed.'
            raise ScreenshotError(err)

        CGImageDestinationAddImage(dest, data, None)
        if CGImageDestinationFinalize(dest):
            return True
        raise ScreenshotError('CGImageDestinationFinalize() failed.')
