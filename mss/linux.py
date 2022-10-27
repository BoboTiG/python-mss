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
    c_ubyte,
    c_uint,
    c_uint32,
    c_ulong,
    c_ushort,
    c_void_p,
)
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple, Union

from .base import MSSBase, lock
from .exception import ScreenShotError
from .models import CFunctions, Monitor
from .screenshot import ScreenShot

__all__ = ("MSS",)


ERROR = SimpleNamespace(details=None)
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


@CFUNCTYPE(c_int, POINTER(Display), POINTER(Event))
def error_handler(_: Any, event: Any) -> int:
    """Specifies the program's supplied error handler."""
    evt = event.contents
    ERROR.details = {
        "type": evt.type,
        "serial": evt.serial,
        "error_code": evt.error_code,
        "request_code": evt.request_code,
        "minor_code": evt.minor_code,
    }
    return 0


def validate(
    retval: int, func: Any, args: Tuple[Any, Any]
) -> Optional[Tuple[Any, Any]]:
    """Validate the returned value of a Xlib or XRANDR function."""

    if retval != 0 and not ERROR.details:
        return args

    details = {"retval": retval, "args": args}
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
    "XGetErrorText": ("xlib", [POINTER(Display), c_int, c_char_p, c_int], c_void_p),
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

    __slots__ = {"drawable", "root", "xlib", "xrandr"}

    # A dict to maintain *display* values created by multiple threads.
    _display_dict: Dict[threading.Thread, int] = {}

    def __init__(self, display: Optional[Union[bytes, str]] = None) -> None:
        """GNU/Linux initialisations."""

        super().__init__()

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
            else:
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
        cur_thread, main_thread = threading.current_thread(), threading.main_thread()
        current_display = MSS._display_dict.get(cur_thread) or MSS._display_dict.get(
            main_thread
        )
        if current_display:
            display = current_display
        else:
            display = self.xlib.XOpenDisplay(disp)
            MSS._display_dict[cur_thread] = display
        return display

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""

        cfactory = self._cfactory
        attrs = {
            "xlib": self.xlib,
            "xrandr": self.xrandr,
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

    def get_error_details(self) -> Optional[Dict[str, Any]]:
        """Get more information about the latest X server error."""

        details: Dict[str, Any] = {}

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
