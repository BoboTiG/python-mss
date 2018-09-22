# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import ctypes
import ctypes.util
import os

from .base import MSSBase
from .exception import ScreenShotError

__all__ = ("MSS",)


PLAINMASK = 0x00ffffff
ZPIXMAP = 2


class Display(ctypes.Structure):
    """
    Structure that serves as the connection to the X server
    and that contains all the information about that X server.
    """


class Event(ctypes.Structure):
    """
    XErrorEvent to debug eventual errors.
    https://tronche.com/gui/x/xlib/event-handling/protocol-errors/default-handlers.html
    """

    _fields_ = [
        ("type", ctypes.c_int),
        ("display", ctypes.POINTER(Display)),
        ("serial", ctypes.c_ulong),
        ("error_code", ctypes.c_ubyte),
        ("request_code", ctypes.c_ubyte),
        ("minor_code", ctypes.c_ubyte),
        ("resourceid", ctypes.c_void_p),
    ]


class XWindowAttributes(ctypes.Structure):
    """ Attributes for the specified window. """

    _fields_ = [
        ("x", ctypes.c_int32),
        ("y", ctypes.c_int32),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("border_width", ctypes.c_int32),
        ("depth", ctypes.c_int32),
        ("visual", ctypes.c_ulong),
        ("root", ctypes.c_ulong),
        ("class", ctypes.c_int32),
        ("bit_gravity", ctypes.c_int32),
        ("win_gravity", ctypes.c_int32),
        ("backing_store", ctypes.c_int32),
        ("backing_planes", ctypes.c_ulong),
        ("backing_pixel", ctypes.c_ulong),
        ("save_under", ctypes.c_int32),
        ("colourmap", ctypes.c_ulong),
        ("mapinstalled", ctypes.c_uint32),
        ("map_state", ctypes.c_uint32),
        ("all_event_masks", ctypes.c_ulong),
        ("your_event_mask", ctypes.c_ulong),
        ("do_not_propagate_mask", ctypes.c_ulong),
        ("override_redirect", ctypes.c_int32),
        ("screen", ctypes.c_ulong),
    ]


class XImage(ctypes.Structure):
    """
    Description of an image as it exists in the client's memory.
    https://tronche.com/gui/x/xlib/graphics/images.html
    """

    _fields_ = [
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("xoffset", ctypes.c_int),
        ("format", ctypes.c_int),
        ("data", ctypes.c_void_p),
        ("byte_order", ctypes.c_int),
        ("bitmap_unit", ctypes.c_int),
        ("bitmap_bit_order", ctypes.c_int),
        ("bitmap_pad", ctypes.c_int),
        ("depth", ctypes.c_int),
        ("bytes_per_line", ctypes.c_int),
        ("bits_per_pixel", ctypes.c_int),
        ("red_mask", ctypes.c_ulong),
        ("green_mask", ctypes.c_ulong),
        ("blue_mask", ctypes.c_ulong),
    ]


class XRRModeInfo(ctypes.Structure):
    """ Voilà, voilà. """


class XRRScreenResources(ctypes.Structure):
    """
    Structure that contains arrays of XIDs that point to the
    available outputs and associated CRTCs.
    """

    _fields_ = [
        ("timestamp", ctypes.c_ulong),
        ("configTimestamp", ctypes.c_ulong),
        ("ncrtc", ctypes.c_int),
        ("crtcs", ctypes.POINTER(ctypes.c_long)),
        ("noutput", ctypes.c_int),
        ("outputs", ctypes.POINTER(ctypes.c_long)),
        ("nmode", ctypes.c_int),
        ("modes", ctypes.POINTER(XRRModeInfo)),
    ]


class XRRCrtcInfo(ctypes.Structure):
    """ Structure that contains CRTC informations. """

    _fields_ = [
        ("timestamp", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("mode", ctypes.c_long),
        ("rotation", ctypes.c_int),
        ("noutput", ctypes.c_int),
        ("outputs", ctypes.POINTER(ctypes.c_long)),
        ("rotations", ctypes.c_ushort),
        ("npossible", ctypes.c_int),
        ("possible", ctypes.POINTER(ctypes.c_long)),
    ]


class MSS(MSSBase):
    """
    Multiple ScreenShots implementation for GNU/Linux.
    It uses intensively the Xlib and its Xrandr extension.
    """

    last_error = None

    def __del__(self):
        # type: () -> None
        """ Clean-up. """

        # Disconnect from the X server
        try:
            self.xlib.XCloseDisplay(self.display)
        except AttributeError:
            pass

    def __init__(self, display=None):
        # type: (bytes) -> None
        """ GNU/Linux initialisations. """

        if not display:
            try:
                display = os.environ["DISPLAY"].encode("utf-8")
            except KeyError:
                raise ScreenShotError("$DISPLAY not set.")

        if not isinstance(display, bytes):
            display = display.encode("utf-8")

        if b":" not in display:
            raise ScreenShotError("Bad display value: {0!r}.".format(display))

        x11 = ctypes.util.find_library("X11")
        if not x11:
            raise ScreenShotError("No X11 library found.")
        self.xlib = ctypes.cdll.LoadLibrary(x11)

        # Install the error handler to prevent interpreter crashes:
        # any error will raise a ScreenShotError exception.
        self.xlib.XSetErrorHandler(error_handler)

        xrandr = ctypes.util.find_library("Xrandr")
        if not xrandr:
            raise ScreenShotError("No Xrandr extension found.")
        self.xrandr = ctypes.cdll.LoadLibrary(xrandr)

        self._set_cfunctions()

        self.display = self.xlib.XOpenDisplay(display)
        self.root = self.xlib.XDefaultRootWindow(
            self.display, self.xlib.XDefaultScreen(self.display)
        )

        # Fix for XRRGetScreenResources and XGetImage:
        #     expected LP_Display instance instead of LP_XWindowAttributes
        self.drawable = ctypes.cast(self.root, ctypes.POINTER(Display))

    def _set_cfunctions(self):
        """ Set all ctypes functions and attach them to attributes. """

        self._cfactory(
            attr=self.xlib,
            func="XSetErrorHandler",
            argtypes=[ctypes.c_void_p],
            restype=ctypes.c_int,
        )
        self._cfactory(
            attr=self.xlib,
            func="XGetErrorText",
            argtypes=[
                ctypes.POINTER(Display),
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
            ],
            restype=ctypes.c_void_p,
        )
        self._cfactory(
            attr=self.xlib,
            func="XOpenDisplay",
            argtypes=[ctypes.c_char_p],
            restype=ctypes.POINTER(Display),
        )
        self._cfactory(
            attr=self.xlib,
            func="XDefaultScreen",
            argtypes=[ctypes.POINTER(Display)],
            restype=ctypes.c_int,
            errcheck=False,
        )
        self._cfactory(
            attr=self.xlib,
            func="XDefaultRootWindow",
            argtypes=[ctypes.POINTER(Display), ctypes.c_int],
            restype=ctypes.POINTER(XWindowAttributes),
        )
        self._cfactory(
            attr=self.xlib,
            func="XGetWindowAttributes",
            argtypes=[
                ctypes.POINTER(Display),
                ctypes.POINTER(XWindowAttributes),
                ctypes.POINTER(XWindowAttributes),
            ],
            restype=ctypes.c_int,
        )
        self._cfactory(
            attr=self.xlib,
            func="XGetImage",
            argtypes=[
                ctypes.POINTER(Display),
                ctypes.POINTER(Display),
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint,
                ctypes.c_uint,
                ctypes.c_ulong,
                ctypes.c_int,
            ],
            restype=ctypes.POINTER(XImage),
        )
        self._cfactory(
            attr=self.xlib,
            func="XDestroyImage",
            argtypes=[ctypes.POINTER(XImage)],
            restype=ctypes.c_void_p,
        )
        self._cfactory(
            attr=self.xlib,
            func="XCloseDisplay",
            argtypes=[ctypes.POINTER(Display)],
            restype=ctypes.c_void_p,
        )
        self._cfactory(
            attr=self.xrandr,
            func="XRRGetScreenResources",
            argtypes=[ctypes.POINTER(Display), ctypes.POINTER(Display)],
            restype=ctypes.POINTER(XRRScreenResources),
        )
        self._cfactory(
            attr=self.xrandr,
            func="XRRGetCrtcInfo",
            argtypes=[
                ctypes.POINTER(Display),
                ctypes.POINTER(XRRScreenResources),
                ctypes.c_long,
            ],
            restype=ctypes.POINTER(XRRCrtcInfo),
        )
        self._cfactory(
            attr=self.xrandr,
            func="XRRFreeScreenResources",
            argtypes=[ctypes.POINTER(XRRScreenResources)],
            restype=ctypes.c_void_p,
        )
        self._cfactory(
            attr=self.xrandr,
            func="XRRFreeCrtcInfo",
            argtypes=[ctypes.POINTER(XRRCrtcInfo)],
            restype=ctypes.c_void_p,
        )

    def _cfactory(self, attr, func, argtypes, restype, errcheck=True):
        # type: (Any, str, List[Any], Any, bool) -> None
        """ Factory to create a ctype function and automatically manage errors. """

        def validate(retval, func, args):
            # type: (int, Any, Tuple[Any, Any]) -> Any
            """ Validate the returned value of a xlib or xrand function. """

            if retval != 0 and not MSS.last_error:
                return args

            err = "{0}() failed".format(func.__name__)
            details = {"retval": retval, "args": args}

            if MSS.last_error:
                details["xerror_details"] = MSS.last_error
                MSS.last_error = None
                xserver_error = ctypes.create_string_buffer(1024)
                self.xlib.XGetErrorText(
                    self.display,
                    details.get("xerror_details", {}).get("error_code", 0),
                    xserver_error,
                    len(xserver_error),
                )
                xerror = xserver_error.value.decode("utf-8")
                if xerror != "0":
                    details["xerror"] = xerror
                    err += ": {0}".format(xerror)

            raise ScreenShotError(err, details=details)

        meth = getattr(attr, func)
        meth.argtypes = argtypes
        meth.restype = restype
        if errcheck:
            meth.errcheck = validate

    @property
    def monitors(self):
        # type: () -> List[Dict[str, int]]
        """ Get positions of monitors (see parent class property). """

        if not self._monitors:
            # All monitors
            gwa = XWindowAttributes()
            self.xlib.XGetWindowAttributes(self.display, self.root, ctypes.byref(gwa))
            self._monitors.append(
                {
                    "left": int(gwa.x),
                    "top": int(gwa.y),
                    "width": int(gwa.width),
                    "height": int(gwa.height),
                }
            )

            # Each monitors
            mon = self.xrandr.XRRGetScreenResources(self.display, self.drawable)
            for idx in range(mon.contents.ncrtc):
                crtc = self.xrandr.XRRGetCrtcInfo(
                    self.display, mon, mon.contents.crtcs[idx]
                )
                if crtc.contents.noutput == 0:
                    self.xrandr.XRRFreeCrtcInfo(crtc)
                    continue

                self._monitors.append(
                    {
                        "left": int(crtc.contents.x),
                        "top": int(crtc.contents.y),
                        "width": int(crtc.contents.width),
                        "height": int(crtc.contents.height),
                    }
                )
                self.xrandr.XRRFreeCrtcInfo(crtc)
            self.xrandr.XRRFreeScreenResources(mon)

        return self._monitors

    def grab(self, monitor):
        # type: (Dict[str, int]) -> ScreenShot
        """ Retrieve all pixels from a monitor. Pixels have to be RGB. """

        # Convert PIL bbox style
        if isinstance(monitor, tuple):
            monitor = {
                "left": monitor[0],
                "top": monitor[1],
                "width": monitor[2] - monitor[0],
                "height": monitor[3] - monitor[1],
            }

        ximage = self.xlib.XGetImage(
            self.display,
            self.drawable,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            PLAINMASK,
            ZPIXMAP,
        )

        bits_per_pixel = ximage.contents.bits_per_pixel
        if bits_per_pixel != 32:
            raise ScreenShotError(
                "[XImage] bits per pixel value not (yet?) implemented: {0}.".format(
                    bits_per_pixel
                )
            )

        data = ctypes.cast(
            ximage.contents.data,
            ctypes.POINTER(ctypes.c_ubyte * monitor["height"] * monitor["width"] * 4),
        )
        data = bytearray(data.contents)

        # Free
        self.xlib.XDestroyImage(ximage)

        return self.cls_image(data, monitor)


@ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(Display), ctypes.POINTER(Event))
def error_handler(display, event):
    # type: (ctypes.POINTER(Display), ctypes.POINTER(Event)) -> int
    """ Specifies the program's supplied error handler. """

    evt = event.contents
    MSS.last_error = {
        "type": evt.type,
        "serial": evt.serial,
        "error_code": evt.error_code,
        "request_code": evt.request_code,
        "minor_code": evt.minor_code,
    }
    return 0
