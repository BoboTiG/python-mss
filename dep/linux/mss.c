
/*
 * This is part of the MSS python's module.
 * This will be compiled into libmss.so and then
 * you can call it from ctypes.
 *
 * See MSSLinux:get_pixels() for a real world example.
 *
 * Source: https://github.com/BoboTiG/python-mss
 */

#include <X11/Xlib.h>
#include <X11/Xutil.h>  /* For XGetPixel prototype */

int GetXImagePixels(
    XImage *ximage,
    const unsigned int width,
    const unsigned int height,
    const unsigned int red_mask,
    const unsigned int green_mask,
    const unsigned int blue_mask,
    unsigned char *pixels
) {
    unsigned int x, y, offset;
    unsigned long pixel;

    if ( !ximage ) {
        return -1;
    }
    if ( !pixels ) {
        return 0;
    }

    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            offset =  x * 3 + width * y * 3;
            pixel = XGetPixel(ximage, x, y);
            pixels[offset]     = (pixel & red_mask) >> 16;
            pixels[offset + 1] = (pixel & green_mask) >> 8;
            pixels[offset + 2] =  pixel & blue_mask;
        }
    }
    return 1;
}
