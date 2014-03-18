
/*
 * This is the MSS python's module implementation in C.
 *
 * Build: gcc -O3 -lX11 test-linux.c -o test-linux
 * Test : python test-raw.py test-linux.raw largeur hauteur
 *
 * http://cgit.freedesktop.org/xorg/lib/libX11/tree/src/ImUtil.c#n444
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <X11/Xlib.h>

int main(void) {
    struct timeval start, end;
    Display *display;
    Window screen, root;
    XWindowAttributes gwa;
    XImage *image;
    int left, top;
    unsigned int x, y, width, height, offset;
    unsigned long allplanes, pixel;
    unsigned char *pixels;

    gettimeofday(&start, NULL);

    display = XOpenDisplay(NULL);
    screen = XDefaultScreen(display);
    root = XDefaultRootWindow(display);
    XGetWindowAttributes(display, root, &gwa);
    left   = gwa.x;
    top    = gwa.y;
    width  = gwa.width;
    height = gwa.height;
    allplanes = XAllPlanes();
    image = XGetImage(display, root, left, top, width, height, allplanes, ZPixmap);
    pixels = malloc(sizeof(unsigned char) * width * height * 3);

    //~ printf("display        = %d\n", display);
    //~ printf("screen         = %d\n", screen);
    //~ printf("root           = %d\n", root);
    //~ printf("left           = %d\n", left);
    //~ printf("top            = %d\n", top);
    //~ printf("width          = %d\n", width);
    //~ printf("height         = %d\n", height);
    //~ printf("allplanes      = %u\n", allplanes);
    //~ printf("bits_per_pixel = %d\n", image->bits_per_pixel);
    //~ printf("bytes_per_line = %d\n", image->bytes_per_line);
    //~ printf("depth          = %d\n", image->depth);

    // Processus habituel
    //~ /*
    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            pixel = XGetPixel(image, x, y);
            offset =  width * y * 3;
            pixels[x * 3 + offset]     = (pixel & image->red_mask) >> 16;
            pixels[x * 3 + offset + 1] = (pixel & image->green_mask) >> 8;
            pixels[x * 3 + offset + 2] =  pixel & image->blue_mask;
        }
    }
    //~ */

    // Processus sans passer par XGetPixel (pas vraiment mieux...)
    /*
    unsigned int shift = 0xffffffff;
    if ( image->depth == 24 ) {
        shift = 0x00ffffff;
    }
    unsigned long px;
    register char *src, *dst;
    register int i, j;
    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            offset =  (y * image->bytes_per_line + ((x * image->bits_per_pixel) >> 3)) + 4;
            src = &image->data[offset];
            dst = (char*)&px;
            px = 0;
            for ( i = (image->bits_per_pixel + 7) >> 3; --i >= 0; )
                *dst++ = *src++;
            pixel = 0;
            for ( i = sizeof(unsigned long); --i >= 0; )
                pixel = (pixel << 8) | ((unsigned char *)&px)[i];
            offset =  width * y * 3;
            pixels[x * 3 + offset]     = (pixel & image->red_mask) >> 16;
            pixels[x * 3 + offset + 1] = (pixel & image->green_mask) >> 8;
            pixels[x * 3 + offset + 2] =  pixel & image->blue_mask;
        }
    }
    //~ */

    XFree(image);
    XCloseDisplay(display);

    gettimeofday(&end, NULL);
    printf("Time : %u msec\n", (1000000 * end.tv_sec + end.tv_usec) - (1000000 * start.tv_sec + start.tv_usec));

    FILE* fh = fopen("test-linux.raw", "wb");
    fwrite(pixels, sizeof(unsigned char), sizeof(unsigned char) * width * height * 3, fh);
    fclose(fh);
    return 0;
}
