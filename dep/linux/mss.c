
/*
 * This is part of the MSS python's module.
 * This will be compiled into mss.so and then
 * you can call it from ctypes.
 *
 * See MSSLinux:get_pixels() for a real world example.
 *
 * Source: https://github.com/BoboTiG/python-mss
 *
 * Build: python setyp.py build_ext
 *    or: gcc -shared -rdynamic -fPIC -s -O3 -lX11 -o mss.so mss.c
 *
 */

#include <X11/Xlib.h>

/* Prototype from Xutil.h */
extern unsigned long XGetPixel(XImage *ximage, int x, int y);

void GetXImagePixels(
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

    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            offset =  x * 3 + width * y * 3;
            pixel = XGetPixel(ximage, x, y);
            pixels[offset]     = (pixel & red_mask) >> 16;
            pixels[offset + 1] = (pixel & green_mask) >> 8;
            pixels[offset + 2] =  pixel & blue_mask;
        }
    }
    return;
}
