
/*
 * This is the MSS python's module implementation in C.
 *
 * Build: gcc -O2 -lX11 -lXrandr test-linux.c -o test-linux
 * Test : python test-raw.py data.raw width height
 *
 * http://cgit.freedesktop.org/xorg/lib/libX11/tree/src/ImUtil.c#n444
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <X11/Xlib.h>
#include <X11/extensions/Xrandr.h>

void full_screen(void) {
    struct timeval start, end;
    Display *display;
    Window screen, root;
    XWindowAttributes gwa;
    XImage *ximage;
    int left, top;
    unsigned int x, y, width, height, offset;
    unsigned long allplanes, pixel;
    unsigned char *pixels, *addr;

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
    ximage = XGetImage(display, root, left, top, width, height, allplanes, ZPixmap);
    pixels = malloc(sizeof(unsigned char) * width * height * 3);

    /*printf("display        = %d\n", display);
    printf("screen         = %d\n", screen);
    printf("root           = %d\n", root);
    printf("left           = %d\n", left);
    printf("top            = %d\n", top);
    printf("width          = %d\n", width);
    printf("height         = %d\n", height);
    printf("allplanes      = %u\n", allplanes);
    printf("bits_per_pixel = %d\n", ximage->bits_per_pixel);
    printf("bytes_per_line = %d\n", ximage->bytes_per_line);
    printf("depth          = %d\n", ximage->depth);
    */

    // Processus habituel
    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            pixel = XGetPixel(ximage, x, y);
            offset =  width * y * 3;
            pixels[x * 3 + offset]     = (pixel & ximage->red_mask) >> 16;
            pixels[x * 3 + offset + 1] = (pixel & ximage->green_mask) >> 8;
            pixels[x * 3 + offset + 2] =  pixel & ximage->blue_mask;
        }
    }

    // Processus sans passer par XGetPixel (ça se vaut)
    /*
    for ( x = 0; x < width; ++x ) {
        for ( y = 0; y < height; ++y ) {
            offset =  width * y * 3;
            addr = &(ximage->data)[y * ximage->bytes_per_line + (x << 2)];
            pixel = addr[3] << 24 | addr[2] << 16 | addr[1] << 8 | addr[0];
            pixels[x * 3 + offset]     = (pixel & ximage->red_mask) >> 16;
            pixels[x * 3 + offset + 1] = (pixel & ximage->green_mask) >> 8;
            pixels[x * 3 + offset + 2] =  pixel & ximage->blue_mask;
        }
    }
    */

    XDestroyImage(ximage);
    XCloseDisplay(display);

    gettimeofday(&end, NULL);
    printf("Fullscreen: %dx%d %u msec\n", width, height, (1000000 * end.tv_sec + end.tv_usec) - (1000000 * start.tv_sec + start.tv_usec));

    FILE* fh = fopen("data-linux_fullscreen.raw", "wb");
    fwrite(pixels, sizeof(unsigned char), sizeof(unsigned char) * width * height * 3, fh);
    fclose(fh);
    return;
}

void each_screen(void) {
    struct timeval start, end;
    Display *display;
    Window root;
    XRRScreenResources *monitors;
    XRRCrtcInfo *crtc_info;
    XImage *ximage;
    int left, top;
    unsigned int n, x, y, width, height, offset;
    unsigned long allplanes, pixel;
    unsigned char *pixels;

    display = XOpenDisplay(NULL);
    root = XDefaultRootWindow(display);
    monitors = XRRGetScreenResources(display, root);
    for ( n = 0; n < monitors->ncrtc; ++n ) {
        gettimeofday(&start, NULL);
        crtc_info = XRRGetCrtcInfo(display, monitors, monitors->crtcs[n]);

        /*printf("motior n°%d\n", n);
        printf("    x = %d\n", crtc_info->x);
        printf("    y = %d\n", crtc_info->y);
        printf("    width = %d\n", crtc_info->width);
        printf("    height = %d\n", crtc_info->height);
        printf("    mode = %d\n", crtc_info->mode);
        printf("    rotation = %d\n", crtc_info->rotation);*/

        left   = crtc_info->x;
        top    = crtc_info->y;
        width  = crtc_info->width;
        height = crtc_info->height;
        allplanes = XAllPlanes();
        ximage = XGetImage(display, root, left, top, width, height, allplanes, ZPixmap);
        pixels = malloc(sizeof(unsigned char) * width * height * 3);

        for ( x = 0; x < width; ++x ) {
            for ( y = 0; y < height; ++y ) {
                offset =  width * y * 3;
                pixel = XGetPixel(ximage, x, y);
                pixels[x * 3 + offset]     = (pixel & ximage->red_mask) >> 16;
                pixels[x * 3 + offset + 1] = (pixel & ximage->green_mask) >> 8;
                pixels[x * 3 + offset + 2] =  pixel & ximage->blue_mask;
            }
        }
        XDestroyImage(ximage);
        XRRFreeCrtcInfo(crtc_info);

        gettimeofday(&end, NULL);
        printf("Screen %d: %dx%d @ %u msec\n", n, width, height, (1000000 * end.tv_sec + end.tv_usec) - (1000000 * start.tv_sec + start.tv_usec));

        char output[128];
        sprintf(output, "data-linux_screen-%d.raw", n);
        FILE* fh = fopen(output, "wb");
        fwrite(pixels, sizeof(unsigned char), sizeof(unsigned char) * width * height * 3, fh);
        fclose(fh);
    }
    XRRFreeScreenResources(monitors);
    XCloseDisplay(display);

    return;
}

int main(void) {
    printf("To test raw data: python test-raw.py data.raw width height\n\n");
    /* The full screen capture */
    full_screen();
    /* A capture for each screen */
    each_screen();
    return 0;
}
