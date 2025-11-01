"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import locale
import os
from contextlib import suppress
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    _Pointer,
    byref,
    c_char_p,
    c_int,
    c_short,
    c_ubyte,
    c_uint,
    c_ulong,
    c_ushort,
    c_void_p,
    cast,
    cdll,
    create_string_buffer,
)
from ctypes.util import find_library
from threading import current_thread, local
from typing import TYPE_CHECKING, Any

from mss.base import MSSBase, lock
from mss.exception import ScreenShotError

if TYPE_CHECKING:  # pragma: nocover
    from mss.models import CFunctions, Monitor
    from mss.screenshot import ScreenShot

__all__ = ("MSS",)


X_FIRST_EXTENSION_OPCODE = 128
PLAINMASK = 0x00FFFFFF
ZPIXMAP = 2
BITS_PER_PIXELS_32 = 32
SUPPORTED_BITS_PER_PIXELS = {
    BITS_PER_PIXELS_32,
}


class XID(c_ulong):
    """X11 generic resource ID
    https://tronche.com/gui/x/xlib/introduction/generic.html
    https://gitlab.freedesktop.org/xorg/proto/xorgproto/-/blob/master/include/X11/X.h#L66
    """


class XStatus(c_int):
    """Xlib common return code type
    This is Status in Xlib, but XStatus here to prevent ambiguity.
    Zero is an error, non-zero is success.
    https://tronche.com/gui/x/xlib/introduction/errors.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L79
    """


class XBool(c_int):
    """Xlib boolean type
    This is Bool in Xlib, but XBool here to prevent ambiguity.
    0 is False, 1 is True.
    https://tronche.com/gui/x/xlib/introduction/generic.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L78
    """


class Display(Structure):
    """Structure that serves as the connection to the X server
    and that contains all the information about that X server.
    The contents of this structure are implementation dependent.
    A Display should be treated as opaque by application code.
    https://tronche.com/gui/x/xlib/display/display-macros.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L477
    https://github.com/garrybodsworth/pyxlib-ctypes/blob/master/pyxlib/xlib.py#L831.
    """

    # Opaque data


class Visual(Structure):
    """Visual structure; contains information about colormapping possible.
    https://tronche.com/gui/x/xlib/window/visual-types.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.hheads#L220
    https://github.com/garrybodsworth/pyxlib-ctypes/blob/master/pyxlib/xlib.py#302.
    """

    # Opaque data (per Tronche)


class Screen(Structure):
    """Information about the screen.
    The contents of this structure are implementation dependent.  A
    Screen should be treated as opaque by application code.
    https://tronche.com/gui/x/xlib/display/screen-information.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L253
    """

    # Opaque data


class XErrorEvent(Structure):
    """XErrorEvent to debug eventual errors.
    https://tronche.com/gui/x/xlib/event-handling/protocol-errors/default-handlers.html.
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L920
    """

    _fields_ = (
        ("type", c_int),
        ("display", POINTER(Display)),  # Display the event was read from
        ("resourceid", XID),  # resource ID
        ("serial", c_ulong),  # serial number of failed request
        ("error_code", c_ubyte),  # error code of failed request
        ("request_code", c_ubyte),  # major op-code of failed request
        ("minor_code", c_ubyte),  # minor op-code of failed request
    )


class XFixesCursorImage(Structure):
    """Cursor structure.
    /usr/include/X11/extensions/Xfixes.h
    https://github.com/freedesktop/xorg-libXfixes/blob/libXfixes-6.0.0/include/X11/extensions/Xfixes.h#L96.
    """

    _fields_ = (
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
    )


class XImage(Structure):
    """Description of an image as it exists in the client's memory.
    https://tronche.com/gui/x/xlib/graphics/images.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L353
    """

    _fields_ = (
        ("width", c_int),  # size of image
        ("height", c_int),  # size of image
        ("xoffset", c_int),  # number of pixels offset in X direction
        ("format", c_int),  # XYBitmap, XYPixmap, ZPixmap
        ("data", c_void_p),  # pointer to image data
        ("byte_order", c_int),  # data byte order, LSBFirst, MSBFirst
        ("bitmap_unit", c_int),  # quant. of scanline 8, 16, 32
        ("bitmap_bit_order", c_int),  # LSBFirst, MSBFirst
        ("bitmap_pad", c_int),  # 8, 16, 32 either XY or ZPixmap
        ("depth", c_int),  # depth of image
        ("bytes_per_line", c_int),  # accelerator to next line
        ("bits_per_pixel", c_int),  # bits per pixel (ZPixmap)
        ("red_mask", c_ulong),  # bits in z arrangement
        ("green_mask", c_ulong),  # bits in z arrangement
        ("blue_mask", c_ulong),  # bits in z arrangement
    )
    # Other opaque fields follow for Xlib's internal use.


class XRRCrtcInfo(Structure):
    """Structure that contains CRTC information.
    https://gitlab.freedesktop.org/xorg/lib/libxrandr/-/blob/master/include/X11/extensions/Xrandr.h#L360.
    """

    _fields_ = (
        ("timestamp", c_ulong),
        ("x", c_int),
        ("y", c_int),
        ("width", c_uint),
        ("height", c_uint),
        ("mode", XID),
        ("rotation", c_ushort),
        ("noutput", c_int),
        ("outputs", POINTER(XID)),
        ("rotations", c_ushort),
        ("npossible", c_int),
        ("possible", POINTER(XID)),
    )


class XRRModeInfo(Structure):
    """https://gitlab.freedesktop.org/xorg/lib/libxrandr/-/blob/master/include/X11/extensions/Xrandr.h#L248."""

    # The fields aren't needed


class XRRScreenResources(Structure):
    """Structure that contains arrays of XIDs that point to the
    available outputs and associated CRTCs.
    https://gitlab.freedesktop.org/xorg/lib/libxrandr/-/blob/master/include/X11/extensions/Xrandr.h#L265.
    """

    _fields_ = (
        ("timestamp", c_ulong),
        ("configTimestamp", c_ulong),
        ("ncrtc", c_int),
        ("crtcs", POINTER(XID)),
        ("noutput", c_int),
        ("outputs", POINTER(XID)),
        ("nmode", c_int),
        ("modes", POINTER(XRRModeInfo)),
    )


class XWindowAttributes(Structure):
    """Attributes for the specified window.
    https://tronche.com/gui/x/xlib/window-information/XGetWindowAttributes.html
    https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/include/X11/Xlib.h#L304
    """

    _fields_ = (
        ("x", c_int),  # location of window
        ("y", c_int),  # location of window
        ("width", c_int),  # width of window
        ("height", c_int),  # height of window
        ("border_width", c_int),  # border width of window
        ("depth", c_int),  # depth of window
        ("visual", POINTER(Visual)),  # the associated visual structure
        ("root", XID),  # root of screen containing window
        ("class", c_int),  # InputOutput, InputOnly
        ("bit_gravity", c_int),  # one of bit gravity values
        ("win_gravity", c_int),  # one of the window gravity values
        ("backing_store", c_int),  # NotUseful, WhenMapped, Always
        ("backing_planes", c_ulong),  # planes to be preserved if possible
        ("backing_pixel", c_ulong),  # value to be used when restoring planes
        ("save_under", XBool),  # boolean, should bits under be saved?
        ("colormap", XID),  # color map to be associated with window
        ("mapinstalled", XBool),  # boolean, is color map currently installed
        ("map_state", c_uint),  # IsUnmapped, IsUnviewable, IsViewable
        ("all_event_masks", c_ulong),  # set of events all people have interest in
        ("your_event_mask", c_ulong),  # my event mask
        ("do_not_propagate_mask", c_ulong),  # set of events that should not propagate
        ("override_redirect", XBool),  # boolean value for override-redirect
        ("screen", POINTER(Screen)),  # back pointer to correct screen
    )


_ERROR = {}
_X11 = find_library("X11")
_XFIXES = find_library("Xfixes")
_XRANDR = find_library("Xrandr")


class XError(ScreenShotError):
    def __str__(self) -> str:
        msg = super().__str__()
        # The details only get populated if the X11 error handler is invoked, but not if a function simply returns
        # a failure status.
        if self.details:
            # We use something similar to the default Xlib error handler's format, since that's quite well-understood.
            # The original code is in
            # https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/master/src/XlibInt.c?ref_type=heads#L1313
            # but we don't try to implement most of it.
            msg += (
                f"\nX Error of failed request:  {self.details['error']}"
                f"\n  Major opcode of failed request:  {self.details['request_code']} ({self.details['request']})"
            )
            if self.details["request_code"] >= X_FIRST_EXTENSION_OPCODE:
                msg += f"\n  Minor opcode of failed request:  {self.details['minor_code']}"
            msg += (
                f"\n  Resource id in failed request:  {self.details['resourceid']}"
                f"\n  Serial number of failed request:  {self.details['serial']}"
            )
        return msg


@CFUNCTYPE(c_int, POINTER(Display), POINTER(XErrorEvent))
def _error_handler(display: Display, event: XErrorEvent) -> int:
    """Specifies the program's supplied error handler."""
    # Get the specific error message
    xlib = cdll.LoadLibrary(_X11)  # type: ignore[arg-type]
    get_error = xlib.XGetErrorText
    get_error.argtypes = [POINTER(Display), c_int, c_char_p, c_int]
    get_error.restype = c_void_p
    get_error_database = xlib.XGetErrorDatabaseText
    get_error_database.argtypes = [POINTER(Display), c_char_p, c_char_p, c_char_p, c_char_p, c_int]
    get_error_database.restype = c_int

    evt = event.contents
    error = create_string_buffer(1024)
    get_error(display, evt.error_code, error, len(error))
    request = create_string_buffer(1024)
    get_error_database(display, b"XRequest", b"%i" % evt.request_code, b"Extension-specific", request, len(request))
    # We don't try to get the string forms of the extension name or minor code currently.  Those are important
    # fields for debugging, but getting the strings is difficult.  The call stack of the exception gives pretty
    # useful similar information, though; most of the requests we use are synchronous, so the failing request is
    # usually the function being called.

    encoding = (
        locale.getencoding() if hasattr(locale, "getencoding") else locale.getpreferredencoding(do_setlocale=False)
    )
    _ERROR[current_thread()] = {
        "error": error.value.decode(encoding, errors="replace"),
        "error_code": evt.error_code,
        "minor_code": evt.minor_code,
        "request": request.value.decode(encoding, errors="replace"),
        "request_code": evt.request_code,
        "serial": evt.serial,
        "resourceid": evt.resourceid,
        "type": evt.type,
    }

    return 0


def _validate_x11(
    retval: _Pointer | None | XBool | XStatus | XID | int, func: Any, args: tuple[Any, Any], /
) -> tuple[Any, Any]:
    thread = current_thread()

    if retval is None:
        # A void return is always ok.
        is_ok = True
    elif isinstance(retval, (_Pointer, XBool, XStatus, XID)):
        # A pointer should be non-NULL.  A boolean should be true.  An Xlib Status should be non-zero.
        # An XID should not be None, which is a reserved ID used for certain APIs.
        is_ok = bool(retval)
    elif isinstance(retval, int):
        # There are currently two functions we call that return ints.  XDestroyImage returns 1 always, and
        # XCloseDisplay returns 0 always.  Neither can fail.  Other Xlib functions might return ints with other
        # interpretations.  If we didn't get an X error from the server, then we'll assume that they worked.
        is_ok = True
    else:
        msg = f"Internal error: cannot check return type {type(retval)}"
        raise AssertionError(msg)

    # Regardless of the return value, raise an error if the thread got an Xlib error (possibly from an earlier call).
    if is_ok and thread not in _ERROR:
        return args

    details = _ERROR.pop(thread, {})
    msg = f"{func.__name__}() failed"
    raise XError(msg, details=details)


# C functions that will be initialised later.
# See https://tronche.com/gui/x/xlib/function-index.html for details.
#
# Available attr: xfixes, xlib, xrandr.
#
# Note: keep it sorted by cfunction.
CFUNCTIONS: CFunctions = {
    # Syntax: cfunction: (attr, argtypes, restype)
    "XCloseDisplay": ("xlib", [POINTER(Display)], c_int),
    "XDefaultRootWindow": ("xlib", [POINTER(Display)], XID),
    "XDestroyImage": ("xlib", [POINTER(XImage)], c_int),
    "XFixesGetCursorImage": ("xfixes", [POINTER(Display)], POINTER(XFixesCursorImage)),
    "XGetImage": (
        "xlib",
        [POINTER(Display), XID, c_int, c_int, c_uint, c_uint, c_ulong, c_int],
        POINTER(XImage),
    ),
    "XGetWindowAttributes": ("xlib", [POINTER(Display), XID, POINTER(XWindowAttributes)], XStatus),
    "XOpenDisplay": ("xlib", [c_char_p], POINTER(Display)),
    "XQueryExtension": ("xlib", [POINTER(Display), c_char_p, POINTER(c_int), POINTER(c_int), POINTER(c_int)], XBool),
    "XRRQueryVersion": ("xrandr", [POINTER(Display), POINTER(c_int), POINTER(c_int)], XStatus),
    "XRRFreeCrtcInfo": ("xrandr", [POINTER(XRRCrtcInfo)], None),
    "XRRFreeScreenResources": ("xrandr", [POINTER(XRRScreenResources)], None),
    "XRRGetCrtcInfo": ("xrandr", [POINTER(Display), POINTER(XRRScreenResources), XID], POINTER(XRRCrtcInfo)),
    "XRRGetScreenResources": ("xrandr", [POINTER(Display), XID], POINTER(XRRScreenResources)),
    "XRRGetScreenResourcesCurrent": ("xrandr", [POINTER(Display), XID], POINTER(XRRScreenResources)),
    "XSetErrorHandler": ("xlib", [c_void_p], c_void_p),
}


class MSS(MSSBase):
    """Multiple ScreenShots implementation for GNU/Linux.
    It uses intensively the Xlib and its Xrandr extension.
    """

    __slots__ = {"_handles", "xfixes", "xlib", "xrandr"}

    def __init__(self, /, **kwargs: Any) -> None:
        """GNU/Linux initialisations."""
        super().__init__(**kwargs)

        # Available thread-specific variables
        self._handles = local()
        self._handles.display = None
        self._handles.drawable = None
        self._handles.original_error_handler = None
        self._handles.root = None

        display = kwargs.get("display", b"")
        if not display:
            try:
                display = os.environ["DISPLAY"].encode("utf-8")
            except KeyError:
                msg = "$DISPLAY not set."
                raise ScreenShotError(msg) from None

        if not isinstance(display, bytes):
            display = display.encode("utf-8")

        if b":" not in display:
            msg = f"Bad display value: {display!r}."
            raise ScreenShotError(msg)

        if not _X11:
            msg = "No X11 library found."
            raise ScreenShotError(msg)
        self.xlib = cdll.LoadLibrary(_X11)

        if not _XRANDR:
            msg = "No Xrandr extension found."
            raise ScreenShotError(msg)
        self.xrandr = cdll.LoadLibrary(_XRANDR)

        if self.with_cursor:
            if _XFIXES:
                self.xfixes = cdll.LoadLibrary(_XFIXES)
            else:
                self.with_cursor = False

        self._set_cfunctions()

        # Install the error handler to prevent interpreter crashes: any error will raise a ScreenShotError exception
        self._handles.original_error_handler = self.xlib.XSetErrorHandler(_error_handler)

        self._handles.display = self.xlib.XOpenDisplay(display)
        if not self._handles.display:
            msg = f"Unable to open display: {display!r}."
            raise ScreenShotError(msg)

        if not self._is_extension_enabled("RANDR"):
            msg = "Xrandr not enabled."
            raise ScreenShotError(msg)

        self._handles.drawable = self._handles.root = self.xlib.XDefaultRootWindow(self._handles.display)

    def close(self) -> None:
        # Clean-up
        if self._handles.display:
            with lock:
                self.xlib.XCloseDisplay(self._handles.display)
            self._handles.display = None
            self._handles.drawable = None
            self._handles.root = None

        # Remove our error handler
        if self._handles.original_error_handler:
            # It's required when exiting MSS to prevent letting `_error_handler()` as default handler.
            # Doing so would crash when using Tk/Tkinter, see issue #220.
            # Interesting technical stuff can be found here:
            #     https://core.tcl-lang.org/tk/file?name=generic/tkError.c&ci=a527ef995862cb50
            #     https://github.com/tcltk/tk/blob/b9cdafd83fe77499ff47fa373ce037aff3ae286a/generic/tkError.c
            self.xlib.XSetErrorHandler(self._handles.original_error_handler)
            self._handles.original_error_handler = None

        # Also empty the error dict
        _ERROR.clear()

    def _is_extension_enabled(self, name: str, /) -> bool:
        """Return True if the given *extension* is enabled on the server."""
        major_opcode_return = c_int()
        first_event_return = c_int()
        first_error_return = c_int()

        try:
            with lock:
                self.xlib.XQueryExtension(
                    self._handles.display,
                    name.encode("latin1"),
                    byref(major_opcode_return),
                    byref(first_event_return),
                    byref(first_error_return),
                )
        except ScreenShotError:
            return False
        return True

    def _set_cfunctions(self) -> None:
        """Set all ctypes functions and attach them to attributes."""
        cfactory = self._cfactory
        attrs = {
            "xfixes": getattr(self, "xfixes", None),
            "xlib": self.xlib,
            "xrandr": self.xrandr,
        }
        for func, (attr, argtypes, restype) in CFUNCTIONS.items():
            with suppress(AttributeError):
                errcheck = None if func == "XSetErrorHandler" else _validate_x11
                cfactory(attrs[attr], func, argtypes, restype, errcheck=errcheck)

    def _monitors_impl(self) -> None:
        """Get positions of monitors. It will populate self._monitors."""
        display = self._handles.display
        int_ = int
        xrandr = self.xrandr

        xrandr_major = c_int(0)
        xrandr_minor = c_int(0)
        xrandr.XRRQueryVersion(display, xrandr_major, xrandr_minor)

        # All monitors
        gwa = XWindowAttributes()
        self.xlib.XGetWindowAttributes(display, self._handles.root, byref(gwa))
        self._monitors.append(
            {"left": int_(gwa.x), "top": int_(gwa.y), "width": int_(gwa.width), "height": int_(gwa.height)},
        )

        # Each monitor
        # A simple benchmark calling 10 times those 2 functions:
        # XRRGetScreenResources():        0.1755971429956844 s
        # XRRGetScreenResourcesCurrent(): 0.0039125580078689 s
        # The second is faster by a factor of 44! So try to use it first.
        # It doesn't query the monitors for updated information, but it does require the server to support
        # RANDR 1.3.  We also make sure the client supports 1.3, by checking for the presence of the function.
        if hasattr(xrandr, "XRRGetScreenResourcesCurrent") and (xrandr_major.value, xrandr_minor.value) >= (1, 3):
            mon = xrandr.XRRGetScreenResourcesCurrent(display, self._handles.drawable).contents
        else:
            mon = xrandr.XRRGetScreenResources(display, self._handles.drawable).contents

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
                },
            )
            xrandr.XRRFreeCrtcInfo(crtc)
        xrandr.XRRFreeScreenResources(mon)

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGB."""
        ximage = self.xlib.XGetImage(
            self._handles.display,
            self._handles.drawable,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            PLAINMASK,
            ZPIXMAP,
        )

        try:
            bits_per_pixel = ximage.contents.bits_per_pixel
            if bits_per_pixel not in SUPPORTED_BITS_PER_PIXELS:
                msg = f"[XImage] bits per pixel value not (yet?) implemented: {bits_per_pixel}."
                raise ScreenShotError(msg)

            raw_data = cast(
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
        ximage = self.xfixes.XFixesGetCursorImage(self._handles.display)
        if not (ximage and ximage.contents):
            msg = "Cannot read XFixesGetCursorImage()"
            raise ScreenShotError(msg)

        cursor_img: XFixesCursorImage = ximage.contents
        region = {
            "left": cursor_img.x - cursor_img.xhot,
            "top": cursor_img.y - cursor_img.yhot,
            "width": cursor_img.width,
            "height": cursor_img.height,
        }

        raw_data = cast(cursor_img.pixels, POINTER(c_ulong * region["height"] * region["width"]))
        raw = bytearray(raw_data.contents)

        data = bytearray(region["height"] * region["width"] * 4)
        data[3::4] = raw[3::8]
        data[2::4] = raw[2::8]
        data[1::4] = raw[1::8]
        data[::4] = raw[::8]

        return self.cls_image(data, region)
