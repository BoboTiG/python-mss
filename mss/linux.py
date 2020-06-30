"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import ctypes
import ctypes.util
import os
import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING

from .base import MSSBase, lock
from .exception import ScreenShotError

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional, Tuple, Union  # noqa

    from .models import Monitor, Monitors  # noqa
    from .screenshot import ScreenShot  # noqa


__all__ = ("MSS",)


ERROR = SimpleNamespace(details=None)
PLAINMASK = 0x00FFFFFF
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
    """ Structure that contains CRTC information. """

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


@ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(Display), ctypes.POINTER(Event))
def error_handler(_, event):
    # type: (Any, Any) -> int
    """ Specifies the program's supplied error handler. """

    evt = event.contents
    ERROR.details = {
        "type": evt.type,
        "serial": evt.serial,
        "error_code": evt.error_code,
        "request_code": evt.request_code,
        "minor_code": evt.minor_code,
    }
    return 0


def validate(retval, func, args):
    # type: (int, Any, Tuple[Any, Any]) -> Optional[Tuple[Any, Any]]
    """ Validate the returned value of a Xlib or XRANDR function. """

    if retval != 0 and not ERROR.details:
        return args

    err = "{}() failed".format(func.__name__)
    details = {"retval": retval, "args": args}
    raise ScreenShotError(err, details=details)


class MSS(MSSBase):
    """
    Multiple ScreenShots implementation for GNU/Linux.
    It uses intensively the Xlib and its Xrandr extension.
    """

    __slots__ = {"drawable", "root", "xlib", "xrandr"}

    # A dict to maintain *display* values created by multiple threads.
    _display_dict = {}  # type: Dict[threading.Thread, int]

    def __init__(self, display=None):
        # type: (Optional[Union[bytes, str]]) -> None
        """ GNU/Linux initialisations. """

        super().__init__()

        if not display:
            try:
                display = os.environ["DISPLAY"].encode("utf-8")
            except KeyError:
                raise ScreenShotError("$DISPLAY not set.")

        if not isinstance(display, bytes):
            display = display.encode("utf-8")

        if b":" not in display:
            raise ScreenShotError("Bad display value: {!r}.".format(display))

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

        self.root = self.xlib.XDefaultRootWindow(self._get_display(display))

        if not self.has_extension("RANDR"):
            raise ScreenShotError("No Xrandr extension found.")

        # Fix for XRRGetScreenResources and XGetImage:
        #     expected LP_Display instance instead of LP_XWindowAttributes
        self.drawable = ctypes.cast(self.root, ctypes.POINTER(Display))

    def has_extension(self, extension):
        # type: (str) -> bool
        """Return True if the given *extension* is part of the extensions list of the server."""
        with lock:
            byref = ctypes.byref
            c_int = ctypes.c_int
            major_opcode_return = c_int()
            first_event_return = c_int()
            first_error_return = c_int()

            try:
                self.xlib.XQueryExtension(
                    self._get_display(),
                    extension.encode("latin1"),
                    byref(major_opcode_return),
                    byref(first_event_return),
                    byref(first_error_return),
                )
            except ScreenShotError:
                return False
            else:
                return True

    def _get_display(self, disp=None):
        """
        Retrieve a thread-safe display from XOpenDisplay().
        In multithreading, if the thread who creates *display* is dead, *display* will
        no longer be valid to grab the screen. The *display* attribute is replaced
        with *_display_dict* to maintain the *display* values in multithreading.
        Since the current thread and main thread are always alive, reuse their
        *display* value first.
        """
        cur_thread, main_thread = threading.current_thread(), threading.main_thread()
        display = MSS._display_dict.get(cur_thread) or MSS._display_dict.get(
            main_thread
        )
        if not display:
            display = MSS._display_dict[cur_thread] = self.xlib.XOpenDisplay(disp)
        return display

    def _set_cfunctions(self):
        """
        Set all ctypes functions and attach them to attributes.
        See https://tronche.com/gui/x/xlib/function-index.html for details.
        """

        def cfactory(func, argtypes, restype, attr=self.xlib):
            # type: (str, List[Any], Any, Any) -> None
            """ Factorize ctypes creations. """
            self._cfactory(
                attr=attr,
                errcheck=validate,
                func=func,
                argtypes=argtypes,
                restype=restype,
            )

        void = ctypes.c_void_p
        c_int = ctypes.c_int
        uint = ctypes.c_uint
        ulong = ctypes.c_ulong
        c_long = ctypes.c_long
        char_p = ctypes.c_char_p
        pointer = ctypes.POINTER

        cfactory("XSetErrorHandler", [void], c_int)
        cfactory("XGetErrorText", [pointer(Display), c_int, char_p, c_int], void)
        cfactory("XOpenDisplay", [char_p], pointer(Display))
        cfactory("XDefaultRootWindow", [pointer(Display)], pointer(XWindowAttributes))
        cfactory(
            "XGetWindowAttributes",
            [pointer(Display), pointer(XWindowAttributes), pointer(XWindowAttributes)],
            c_int,
        )
        cfactory(
            "XGetImage",
            [
                pointer(Display),
                pointer(Display),
                c_int,
                c_int,
                uint,
                uint,
                ulong,
                c_int,
            ],
            pointer(XImage),
        )
        cfactory("XDestroyImage", [pointer(XImage)], void)
        cfactory(
            "XQueryExtension",
            [pointer(Display), char_p, pointer(c_int), pointer(c_int), pointer(c_int)],
            uint,
        )

        # A simple benchmark calling 10 times those 2 functions:
        # XRRGetScreenResources():        0.1755971429956844 s
        # XRRGetScreenResourcesCurrent(): 0.0039125580078689 s
        # The second is faster by a factor of 44! So try to use it first.
        try:
            cfactory(
                "XRRGetScreenResourcesCurrent",
                [pointer(Display), pointer(Display)],
                pointer(XRRScreenResources),
                attr=self.xrandr,
            )
        except AttributeError:
            cfactory(
                "XRRGetScreenResources",
                [pointer(Display), pointer(Display)],
                pointer(XRRScreenResources),
                attr=self.xrandr,
            )
            self.xrandr.XRRGetScreenResourcesCurrent = self.xrandr.XRRGetScreenResources

        cfactory(
            "XRRGetCrtcInfo",
            [pointer(Display), pointer(XRRScreenResources), c_long],
            pointer(XRRCrtcInfo),
            attr=self.xrandr,
        )
        cfactory(
            "XRRFreeScreenResources",
            [pointer(XRRScreenResources)],
            void,
            attr=self.xrandr,
        )
        cfactory("XRRFreeCrtcInfo", [pointer(XRRCrtcInfo)], void, attr=self.xrandr)

    def get_error_details(self):
        # type: () -> Optional[Dict[str, Any]]
        """ Get more information about the latest X server error. """

        details = {}  # type: Dict[str, Any]

        if ERROR.details:
            details = {"xerror_details": ERROR.details}
            ERROR.details = None
            xserver_error = ctypes.create_string_buffer(1024)
            self.xlib.XGetErrorText(
                self._get_display(),
                details.get("xerror_details", {}).get("error_code", 0),
                xserver_error,
                len(xserver_error),
            )
            xerror = xserver_error.value.decode("utf-8")
            if xerror != "0":
                details["xerror"] = xerror

        return details

    def _monitors_impl(self):
        # type: () -> None
        """ Get positions of monitors. It will populate self._monitors. """

        display = self._get_display()
        int_ = int
        xrandr = self.xrandr

        # All monitors
        gwa = XWindowAttributes()
        self.xlib.XGetWindowAttributes(display, self.root, ctypes.byref(gwa))
        self._monitors.append(
            {
                "left": int_(gwa.x),
                "top": int_(gwa.y),
                "width": int_(gwa.width),
                "height": int_(gwa.height),
            }
        )

        # Each monitors
        mon = xrandr.XRRGetScreenResourcesCurrent(display, self.drawable).contents
        crtcs = mon.crtcs
        for idx in range(mon.ncrtc):
            crtc = xrandr.XRRGetCrtcInfo(display, mon, crtcs[idx]).contents
            if crtc.noutput == 0:
                xrandr.XRRFreeCrtcInfo(crtc)
                continue

            self._monitors.append(
                {
                    "left": int_(crtc.x),
                    "top": int_(crtc.y),
                    "width": int_(crtc.width),
                    "height": int_(crtc.height),
                }
            )
            xrandr.XRRFreeCrtcInfo(crtc)
        xrandr.XRRFreeScreenResources(mon)

    def _grab_impl(self, monitor):
        # type: (Monitor) -> ScreenShot
        """ Retrieve all pixels from a monitor. Pixels have to be RGB. """

        ximage = self.xlib.XGetImage(
            self._get_display(),
            self.drawable,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            PLAINMASK,
            ZPIXMAP,
        )

        try:
            bits_per_pixel = ximage.contents.bits_per_pixel
            if bits_per_pixel != 32:
                raise ScreenShotError(
                    "[XImage] bits per pixel value not (yet?) implemented: {}.".format(
                        bits_per_pixel
                    )
                )

            raw_data = ctypes.cast(
                ximage.contents.data,
                ctypes.POINTER(
                    ctypes.c_ubyte * monitor["height"] * monitor["width"] * 4
                ),
            )
            data = bytearray(raw_data.contents)
        finally:
            # Free
            self.xlib.XDestroyImage(ximage)

        return self.cls_image(data, monitor)
