"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import contextlib
import ctypes
import ctypes.util
import os
import threading
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char_p,
    c_int,
    c_int32,
    c_long,
    c_short,
    c_ubyte,
    c_uint,
    c_uint32,
    c_ulong,
    c_ushort,
    c_void_p,
    cast,
)
from typing import Any, Dict, Optional, Tuple, Union

from .base import MSSBase, lock
from .exception import ScreenShotError
from .models import CFunctions, Monitor
from .screenshot import ScreenShot

__all__ = ("MSS",)


PLAINMASK = 0x00FFFFFF
ZPIXMAP = 2


class Display(Structure):
    """
    Structure that serves as the connection to the X server
    and that contains all the information about that X server.
    """


class Event(Structure):
    """
    XErrorEvent to debug eventual errors.
    https://tronche.com/gui/x/xlib/event-handling/protocol-errors/default-handlers.html
    """

    _fields_ = [
        ("type", c_int),
        ("display", POINTER(Display)),
        ("serial", c_ulong),
        ("error_code", c_ubyte),
        ("request_code", c_ubyte),
        ("minor_code", c_ubyte),
        ("resourceid", c_void_p),
    ]


class XFixesCursorImage(Structure):
    """
    XFixes is an X Window System extension.
    See /usr/include/X11/extensions/Xfixes.h
    """

    _fields_ = [
        ("x", c_short),
        ("y", c_short),
        ("width", c_ushort),
        ("height", c_ushort),
        ("xhot", c_ushort),
        ("yhot", c_ushort),
        ("cursor_serial", c_ulong),
        ("pixels", POINTER(c_ulong)),
        ("atom", c_ulong),
        ("name", c_char_p),
    ]


class XWindowAttributes(Structure):
    """Attributes for the specified window."""

    _fields_ = [
        ("x", c_int32),
        ("y", c_int32),
        ("width", c_int32),
        ("height", c_int32),
        ("border_width", c_int32),
        ("depth", c_int32),
        ("visual", c_ulong),
        ("root", c_ulong),
        ("class", c_int32),
        ("bit_gravity", c_int32),
        ("win_gravity", c_int32),
        ("backing_store", c_int32),
        ("backing_planes", c_ulong),
        ("backing_pixel", c_ulong),
        ("save_under", c_int32),
        ("colourmap", c_ulong),
        ("mapinstalled", c_uint32),
        ("map_state", c_uint32),
        ("all_event_masks", c_ulong),
        ("your_event_mask", c_ulong),
        ("do_not_propagate_mask", c_ulong),
        ("override_redirect", c_int32),
        ("screen", c_ulong),
    ]


class XImage(Structure):
    """
    Description of an image as it exists in the client's memory.
    https://tronche.com/gui/x/xlib/graphics/images.html
    """

    _fields_ = [
        ("width", c_int),
        ("height", c_int),
        ("xoffset", c_int),
        ("format", c_int),
        ("data", c_void_p),
        ("byte_order", c_int),
        ("bitmap_unit", c_int),
        ("bitmap_bit_order", c_int),
        ("bitmap_pad", c_int),
        ("depth", c_int),
        ("bytes_per_line", c_int),
        ("bits_per_pixel", c_int),
        ("red_mask", c_ulong),
        ("green_mask", c_ulong),
        ("blue_mask", c_ulong),
    ]


class XRRModeInfo(Structure):
    """Voilà, voilà."""


class XRRScreenResources(Structure):
    """
    Structure that contains arrays of XIDs that point to the
    available outputs and associated CRTCs.
    """

    _fields_ = [
        ("timestamp", c_ulong),
        ("configTimestamp", c_ulong),
        ("ncrtc", c_int),
        ("crtcs", POINTER(c_long)),
        ("noutput", c_int),
        ("outputs", POINTER(c_long)),
        ("nmode", c_int),
        ("modes", POINTER(XRRModeInfo)),
    ]


class XRRCrtcInfo(Structure):
    """Structure that contains CRTC information."""

    _fields_ = [
        ("timestamp", c_ulong),
        ("x", c_int),
        ("y", c_int),
        ("width", c_int),
        ("height", c_int),
        ("mode", c_long),
        ("rotation", c_int),
        ("noutput", c_int),
        ("outputs", POINTER(c_long)),
        ("rotations", c_ushort),
        ("npossible", c_int),
        ("possible", POINTER(c_long)),
    ]


_ERROR = {}


@CFUNCTYPE(c_int, POINTER(Display), POINTER(Event))
def error_handler(display: Display, event: Event) -> int:
    """Specifies the program's supplied error handler."""
    x11 = ctypes.util.find_library("X11")
    if not x11:
        return 0

    # Get the specific error message
    xlib = ctypes.cdll.LoadLibrary(x11)
    get_error = getattr(xlib, "XGetErrorText")
    get_error.argtypes = [POINTER(Display), c_int, c_char_p, c_int]
    get_error.restype = c_void_p

    evt = event.contents
    error = ctypes.create_string_buffer(1024)
    get_error(display, evt.error_code, error, len(error))

    _ERROR[threading.current_thread()] = {
        "error": error.value.decode("utf-8"),
        "error_code": evt.error_code,
        "minor_code": evt.minor_code,
        "request_code": evt.request_code,
        "serial": evt.serial,
        "type": evt.type,
    }

    return 0


def validate(retval: int, func: Any, args: Tuple[Any, Any]) -> Tuple[Any, Any]:
    """Validate the returned value of a Xlib or XRANDR function."""

    current_thread = threading.current_thread()
    if retval != 0 and current_thread not in _ERROR:
        return args

    details = _ERROR.pop(current_thread, {})
    raise ScreenShotError(f"{func.__name__}() failed", details=details)


# C functions that will be initialised later.
# See https://tronche.com/gui/x/xlib/function-index.html for details.
#
# This is a dict:
#    cfunction: (attr, argtypes, restype)
#
# Available attr: xlib, xrandr.
#
# Note: keep it sorted by cfunction.
CFUNCTIONS: CFunctions = {
    "XDefaultRootWindow": ("xlib", [POINTER(Display)], POINTER(XWindowAttributes)),
    "XDestroyImage": ("xlib", [POINTER(XImage)], c_void_p),
    "XFixesGetCursorImage": ("xfixes", [POINTER(Display)], POINTER(XFixesCursorImage)),
    "XGetImage": (
        "xlib",
        [
            POINTER(Display),
            POINTER(Display),
            c_int,
            c_int,
            c_uint,
            c_uint,
            c_ulong,
            c_int,
        ],
        POINTER(XImage),
    ),
    "XGetWindowAttributes": (
        "xlib",
        [POINTER(Display), POINTER(XWindowAttributes), POINTER(XWindowAttributes)],
        c_int,
    ),
    "XOpenDisplay": ("xlib", [c_char_p], POINTER(Display)),
    "XQueryExtension": (
        "xlib",
        [
            POINTER(Display),
            c_char_p,
            POINTER(c_int),
            POINTER(c_int),
            POINTER(c_int),
        ],
        c_uint,
    ),
    "XRRFreeCrtcInfo": ("xrandr", [POINTER(XRRCrtcInfo)], c_void_p),
    "XRRFreeScreenResources": ("xrandr", [POINTER(XRRScreenResources)], c_void_p),
    "XRRGetCrtcInfo": (
        "xrandr",
        [POINTER(Display), POINTER(XRRScreenResources), c_long],
        POINTER(XRRCrtcInfo),
    ),
    "XRRGetScreenResources": (
        "xrandr",
        [POINTER(Display), POINTER(Display)],
        POINTER(XRRScreenResources),
    ),
    "XRRGetScreenResourcesCurrent": (
        "xrandr",
        [POINTER(Display), POINTER(Display)],
        POINTER(XRRScreenResources),
    ),
    "XSetErrorHandler": ("xlib", [c_void_p], c_int),
}


class MSS(MSSBase):
    """
    Multiple ScreenShots implementation for GNU/Linux.
    It uses intensively the Xlib and its Xrandr extension.
    """

    __slots__ = {"drawable", "root", "xlib", "xrandr", "xfixes", "__with_cursor"}

    # A dict to maintain *display* values created by multiple threads.
    _display_dict: Dict[threading.Thread, int] = {}

    def __init__(
        self, display: Optional[Union[bytes, str]] = None, with_cursor: bool = False
    ) -> None:
        """GNU/Linux initialisations."""

        super().__init__()
        self.with_cursor = with_cursor

        if not display:
            try:
                display = os.environ["DISPLAY"].encode("utf-8")
            except KeyError:
                # pylint: disable=raise-missing-from
                raise ScreenShotError("$DISPLAY not set.")

        if not isinstance(display, bytes):
            display = display.encode("utf-8")

        if b":" not in display:
            raise ScreenShotError(f"Bad display value: {display!r}.")

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

        if self.with_cursor:
            xfixes = ctypes.util.find_library("Xfixes")
            if xfixes:
                self.xfixes = ctypes.cdll.LoadLibrary(xfixes)
            else:
                self.with_cursor = False

        self._set_cfunctions()

        self.root = self.xlib.XDefaultRootWindow(self._get_display(display))

        if not self.has_extension("RANDR"):
            raise ScreenShotError("No Xrandr extension found.")

        # Fix for XRRGetScreenResources and XGetImage:
        #     expected LP_Display instance instead of LP_XWindowAttributes
        self.drawable = ctypes.cast(self.root, POINTER(Display))

    def has_extension(self, extension: str) -> bool:
        """Return True if the given *extension* is part of the extensions list of the server."""
        with lock:
            major_opcode_return = c_int()
            first_event_return = c_int()
            first_error_return = c_int()

            try:
                self.xlib.XQueryExtension(
                    self._get_display(),
                    extension.encode("latin1"),
                    ctypes.byref(major_opcode_return),
                    ctypes.byref(first_event_return),
                    ctypes.byref(first_error_return),
                )
            except ScreenShotError:
                return False
            return True

    def _get_display(self, disp: Optional[bytes] = None) -> int:
        """
        Retrieve a thread-safe display from XOpenDisplay().
        In multithreading, if the thread that creates *display* is dead, *display* will
        no longer be valid to grab the screen. The *display* attribute is replaced
        with *_display_dict* to maintain the *display* values in multithreading.
        Since the current thread and main thread are always alive, reuse their
        *display* value first.
        """
        current_thread = threading.current_thread()
        current_display = MSS._display_dict.get(current_thread)
        if current_display:
            display = current_display
        else:
            display = self.xlib.XOpenDisplay(disp)
            MSS._display_dict[current_thread] = display
        return display

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""

        cfactory = self._cfactory
        attrs = {
            "xlib": self.xlib,
            "xrandr": self.xrandr,
            "xfixes": getattr(self, "xfixes", None),
        }
        for func, (attr, argtypes, restype) in CFUNCTIONS.items():
            with contextlib.suppress(AttributeError):
                cfactory(
                    attr=attrs[attr],
                    errcheck=validate,
                    func=func,
                    argtypes=argtypes,
                    restype=restype,
                )

    def _monitors_impl(self) -> None:
        """Get positions of monitors. It will populate self._monitors."""

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

        # Each monitor
        # A simple benchmark calling 10 times those 2 functions:
        # XRRGetScreenResources():        0.1755971429956844 s
        # XRRGetScreenResourcesCurrent(): 0.0039125580078689 s
        # The second is faster by a factor of 44! So try to use it first.
        try:
            mon = xrandr.XRRGetScreenResourcesCurrent(display, self.drawable).contents
        except AttributeError:
            mon = xrandr.XRRGetScreenResources(display, self.drawable).contents

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

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB."""

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
                    f"[XImage] bits per pixel value not (yet?) implemented: {bits_per_pixel}."
                )

            raw_data = ctypes.cast(
                ximage.contents.data,
                POINTER(c_ubyte * monitor["height"] * monitor["width"] * 4),
            )
            data = bytearray(raw_data.contents)
        finally:
            # Free
            self.xlib.XDestroyImage(ximage)

        return self.cls_image(data, monitor)

    def _cursor_impl(self) -> ScreenShot:
        """Retrieve all cursor data. Pixels have to be RGB."""

        # Read data of cursor/mouse-pointer
        cursor_data = self.xfixes.XFixesGetCursorImage(self._get_display())
        if not (cursor_data and cursor_data.contents):
            raise ScreenShotError("Cannot read XFixesGetCursorImage()")

        ximage: XFixesCursorImage = cursor_data.contents
        monitor = {
            "left": ximage.x - ximage.xhot,
            "top": ximage.y - ximage.yhot,
            "width": ximage.width,
            "height": ximage.height,
        }

        raw_data = cast(
            ximage.pixels, POINTER(c_ulong * monitor["height"] * monitor["width"])
        )
        raw = bytearray(raw_data.contents)

        data = bytearray(monitor["height"] * monitor["width"] * 4)
        data[3::4] = raw[3::8]
        data[2::4] = raw[2::8]
        data[1::4] = raw[1::8]
        data[::4] = raw[::8]

        return self.cls_image(data, monitor)
