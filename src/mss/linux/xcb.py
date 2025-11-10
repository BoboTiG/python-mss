#! /usr/bin/env python3

from __future__ import annotations

import ctypes.util
from contextlib import suppress
from copy import copy
from ctypes import (
    CDLL,
    POINTER,
    Array,
    Structure,
    _Pointer,
    addressof,
    c_char,
    c_char_p,
    c_int,
    c_int16,
    c_uint,
    c_uint8,
    c_uint16,
    c_uint32,
    c_void_p,
    cast,
    cdll,
)
from threading import Lock
from typing import TYPE_CHECKING
from weakref import finalize

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import Any

from mss.exception import ScreenShotError

# In general, anything global starting with Xcb, XCB_, or xcb_ is a
# reflection of something in XCB with the same name.
#
# The functions starting with xcb_ that are based on list_xcb don't
# have exact parallels in XCB, but that's because of C limitations.
# XCB does export the same name with _iterator appended; for instance,
# XCB doesn't have xcb_setup_roots, but it does have
# xcb_setup_roots_iterator.
#
# Among other things, this makes it easier to autogenerate them.


def depends_on(subobject: Any, superobject: Any) -> None:
    """Make sure that superobject is not GC'd before subobject.

    In XCB, a structure often is allocated with additional trailing
    data following it, with special accessors to get pointers to that
    extra data.

    In ctypes, if you access a structure field, a pointer value, etc.,
    then the outer object won't be garbage collected until after the
    inner object.  (This uses the ctypes _b_base_ mechanism.)

    However, when using the XCB accessor functions, you don't get that
    guarantee automatically.  Once all references to the outer
    structure have dropped, then we will free the memory for it (the
    response structures XCB returns have to be freed by us), including
    the trailing data.  If there are live references to the trailing
    data, then those will become invalid.

    To prevent this, we use depends_on to make sure that the
    outer structure is not released before all the references to the
    inner objects have been cleared.
    """
    # The implementation is quite simple.  We create a finalizer on
    # the inner object, with a callback that references the outer
    # object.  That ensures that there are live references to the
    # outer object until the references to the inner object have been
    # gc'd.  We can't just create a ref, though; it seems that their
    # callbacks will only run if the ref itself is still referenced.
    # We need the extra machinery that finalize provides, which uses
    # an internal registry to keep the refs alive.
    return finalize(subobject, id, superobject)


#### XCB basic structures


class XcbConnection(Structure):
    pass  # Opaque


class XcbGenericErrorStructure(Structure):
    # The XCB name is xcb_generic_error.  It is named differently here
    # to make it clear that this is not an exception class, since in
    # Python, those traditionally end in ...Error.
    _fields_ = (
        ("response_type", c_uint8),
        ("error_code", c_uint8),
        ("sequence", c_uint16),
        ("resource_id", c_uint32),
        ("minor_code", c_uint16),
        ("major_code", c_uint8),
        ("pad0", c_uint8),
        ("pad", c_uint32 * 5),
        ("full_sequence", c_uint32),
    )


#### Request / response handling
#
# This section isn't needed to understand the main() function below.
# It's using higher-level functions.  This section defines the way
# that those functions are built.
#
# The following recaps a lot of what's in the xcb-requests(3) man
# page, with a few notes about what we're doing in this library.
#
# In XCB, when you send a request to the server, the function returns
# immediately.  You don't get back the server's reply; you get back a
# "cookie".  (This just holds the sequence number of the request.)
# Later, you can use that cookie to get the reply or error back.
#
# This lets you fire off requests in rapid succession, and then
# afterwards check the results.  It also lets you do other work (like
# process a screenshot) while a request is in flight (like getting the
# next screenshot).  This is asynchronous processing, and is great for
# performance.
#
# In this program, we currently don't try to do anything
# asynchronously, although the design doesn't preclude it.  (You'd add
# a synchronous=False flag to the entrypoint wrappers below, and not
# call .check / .reply, but rather just return the cookie.)
#
# XCB has two types of requests.  Void requests don't return anything
# from the server.  These are things like "create a window".  The
# typed requests do request information from the server.  These are
# things like "get a window's size".
#
# Void requests all return the same type of cookie.  The only thing
# you can do with the cookie is check to see if you got an error.
#
# Typed requests return a call-specific cookie with the same
# structure.  They are call-specific so they can be type-checked.
# (This is the case in both XCB C and in this library.)
#
# XCB has a concept of "checked" or "unchecked" request functions.  By
# default, void requests are unchecked.  For an unchecked function,
# XCB doesn't do anything to let you know that the request completed
# successfully.  If there's an error, then you need to handle it in
# your main loop, as a regular event.  We always use the checked
# versions instead, so that we can raise an exception at the right
# place in the code.
#
# Similarly, typed requests default to checked, but have unchecked
# versions.  That's just to align their error handling with the
# unchecked void functions; you always need to do something with the
# cookie so you can get the response.
#
# As mentioned, we always use the checked requests; that's unlikely to
# change, since error-checking with unchecked requests requires
# control of the event loop.
#
# Below are wrappers that set up the request / response functions in
# ctypes, and define the cookie types to do error handling.


class XError(ScreenShotError):
    """Base exception class for anything related to X11.

    This is not prefixed with Xcb to prevent confusion with the XCB
    error structures.
    """


class XProtoError(XError):
    """Exception indicating server-reported errors."""

    def __init__(self, xcb_conn: XcbConnection, xcb_err: XcbGenericErrorStructure) -> None:
        if isinstance(xcb_err, _Pointer):
            xcb_err = xcb_err.contents
        assert isinstance(xcb_err, XcbGenericErrorStructure)  # noqa: S101

        details = {
            "error_code": xcb_err.error_code,
            "sequence": xcb_err.sequence,
            "resource_id": xcb_err.resource_id,
            "minor_code": xcb_err.minor_code,
            "major_code": xcb_err.major_code,
            "full_sequence": xcb_err.full_sequence,
        }

        # xcb-errors is a library to get descriptive error strings, instead of reporting the raw codes.  This is not
        # installed by default on most systems, but is quite helpful for developers.  We use it if it exists, but don't
        # force the matter.  We can't do this when we format the error message, since the XCB connection may be gone.
        if LIB.errors:
            # We don't try to reuse the error context, since it's per-connection, and probably will only be used once.
            ctx = POINTER(XcbErrorsContext)()
            ctx_new_setup = LIB.errors.xcb_errors_context_new(xcb_conn, ctx)
            if ctx_new_setup == 0:
                try:
                    # Some of these may return NULL, but some are guaranteed.
                    ext_name = POINTER(c_char_p)()
                    error_name = LIB.errors.xcb_errors_get_name_for_error(ctx, xcb_err.error_code, ext_name)
                    details["error"] = error_name.decode("ascii", errors="replace")
                    if ext_name:
                        details["extension"] = ext_name.decode("ascii", errors="replace")
                    major_name = LIB.errors.xcb_errors_get_name_for_major_code(ctx, xcb_err.major_code)
                    details["major_name"] = major_name.decode("ascii", errors="replace")
                    minor_name = LIB.errors.xcb_errors_get_name_for_minor_code(
                        ctx, xcb_err.major_code, xcb_err.minor_code
                    )
                    if minor_name:
                        details["minor_name"] = minor_name.decode("ascii", errors="replace")
                finally:
                    LIB.errors.xcb_errors_context_free(ctx)

        super().__init__("X11 Protocol Error", details=details)

    def __str__(self) -> str:
        msg = super().__str__()
        details = self.details
        error_desc = f"{details['error_code']} ({details['error']})" if "error" in details else details["error_code"]
        major_desc = (
            f"{details['major_code']} ({details['major_name']})" if "major_name" in details else details["major_code"]
        )
        minor_desc = (
            f"{details['minor_code']} ({details['minor_name']})" if "minor_name" in details else details["minor_code"]
        )
        ext_desc = f"\n  Extension:  {details['ext_name']}" if "ext_desc" in details else ""
        msg += (
            f"\nX Error of failed request:  {error_desc}"
            f"\n  Major opcode of failed request:  {major_desc}"
            f"{ext_desc}"
            f"\n  Minor opcode of failed request:  {minor_desc}"
            f"\n  Resource id in failed request:  {details['resource_id']}"
            f"\n  Serial number of failed request:  {details['full_sequence']}"
        )
        return msg


class CookieBase(Structure):
    """Generic XCB cookie.

    XCB does not export this as a base type.  However, all XCB cookies
    have the same structure, so this encompasses the common structure
    in Python.
    """

    # I've considered adding a finalizer that will raise an exception
    # if this object goes out of scope without being disposed of.

    _fields_ = (("sequence", c_uint),)

    def discard(self, xcb_conn: XcbConnection) -> None:
        """Free memory associated with this request, and ignore errors."""
        LIB.xcb.xcb_discard_reply(xcb_conn, self.sequence)


class XcbVoidCookie(CookieBase):
    """XCB cookie for requests with no responses.

    This corresponds to xcb_void_cookie_t.
    """

    def check(self, xcb_conn: XcbConnection) -> None:
        """Verify that the function completed successfully.

        This will raise an exception if there is an error.
        """
        err_p = LIB.xcb.xcb_request_check(xcb_conn, self)
        if not err_p:
            return
        err = copy(err_p.contents)
        LIB.c.free(err_p)
        raise XProtoError(xcb_conn, err)


def initialize_xcb_void_func(lib: CDLL, name: str, request_argtypes: list) -> None:
    """Set up ctypes for a void-typed XCB function.

    This is only applicable to checked variants of functions that do
    not have a response type.

    This arranges for the ctypes function to take the given argtypes,
    and to return an XcbVoidCookie that can be used to check for
    errors later.
    """
    # I would check that name.endswith("_checked") here, but ruff
    # doesn't want me to use assert, or to give an error message
    # to an exception.
    func = getattr(lib, name)
    func.argtypes = request_argtypes
    func.restype = XcbVoidCookie


class ReplyCookieBase(CookieBase):
    _xcb_reply_func_ = None

    def reply(self, xcb_conn: XcbConnection) -> Structure:
        """Wait for and return the server's response.

        The response will be freed (with libc's free) when it, and its
        descendents, are no longer referenced.

        If the server indicates an error, an exception is raised
        instead.
        """
        err_p = POINTER(XcbGenericErrorStructure)()
        reply_p = self._xcb_reply_func_(xcb_conn, self, err_p)
        if err_p:
            # I think this is always NULL, but we can free it.
            if reply_p:
                LIB.c.free(reply_p)
            # Copying the error structure is cheap, and makes memory
            # management easier.
            err_copy = copy(err_p.contents)
            LIB.c.free(err_p)
            raise XProtoError(xcb_conn, err_copy)
        # I would assert that reply_p is set here, but ruff doesn't
        # allow asserts.

        # It's not known, at this point, how long the reply structure
        # actually is: there may be trailing data that needs to be
        # processed and then freed.  We have to set a finalizer on the
        # reply, so it can be freed when Python is done with it.  The
        # correctness of this also depends on the _b_base_ pointers in
        # derived fields, which ctypes manages.
        reply_void_p = c_void_p(addressof(reply_p.contents))
        finalizer = finalize(reply_p, LIB.c.free, reply_void_p)
        finalizer.atexit = False
        return reply_p.contents


def initialize_xcb_typed_func(lib: CDLL, name: str, request_argtypes: list, reply_struct: type) -> None:
    """Set up ctypes for a response-returning XCB function.

    This is only applicable to checked (the default) variants of
    functions that have a response type.

    This arranges for the ctypes function to take the given argtypes.
    The ctypes function will then return an XcbTypedCookie (rather,
    a function-specific subclass of it).  That can be used to call the
    XCB xcb_blahblah_reply function to check for errors and return the
    server's response.
    """

    base_name = name
    title_name = base_name.title().replace("_", "")
    request_func = getattr(lib, name)
    reply_func = getattr(lib, f"{name}_reply")
    # The cookie type isn't used outside this function, so we can just
    # declare it here implicitly.
    cookie_type = type(f"{title_name}Cookie", (ReplyCookieBase,), {"_xcb_reply_func_": reply_func})
    request_func.argtypes = request_argtypes
    request_func.restype = cookie_type
    reply_func.argtypes = [POINTER(XcbConnection), cookie_type, POINTER(POINTER(XcbGenericErrorStructure))]
    reply_func.restype = POINTER(reply_struct)


### XCB types

# These are in the same order as they appear in the XML definitions,
# as much as practical.  In a future release, we might want to
# auto-generate them from the XML.

# xcb client-side types


class XcbExtension(Structure):
    _fields_ = (("name", c_char_p), ("global_id", c_int))


# xproto: Core protocol types


class XID(c_uint32):
    pass


class XcbDrawable(XID):
    pass


class XcbWindow(XcbDrawable):
    pass


class XcbPixmap(XcbDrawable):
    pass


class XcbColormap(XID):
    pass


class XcbAtom(XID):
    pass


class XcbVisualid(c_uint32):
    pass


class XcbTimestamp(c_uint32):
    pass


class XcbKeycode(c_uint8):
    pass


# xproto: Connection setup-related types


class XcbFormat(Structure):
    _fields_ = (("depth", c_uint8), ("bits_per_pixel", c_uint8), ("scanline_pad", c_uint8), ("pad0", c_uint8 * 5))


class XcbVisualtype(Structure):
    _fields_ = (
        ("visual_id", XcbVisualid),
        ("class_", c_uint8),
        ("bits_per_rgb_value", c_uint8),
        ("colormap_entries", c_uint16),
        ("red_mask", c_uint32),
        ("green_mask", c_uint32),
        ("blue_mask", c_uint32),
        ("pad0", c_uint8 * 4),
    )


class XcbDepth(Structure):
    _fields_ = (("depth", c_uint8), ("pad0", c_uint8), ("visuals_len", c_uint16), ("pad1", c_uint8 * 4))


class XcbDepthIterator(Structure):
    _fields_ = (("data", POINTER(XcbDepth)), ("rem", c_int), ("index", c_int))


class XcbScreen(Structure):
    _fields_ = (
        ("root", XcbWindow),
        ("default_colormap", XcbColormap),
        ("white_pixel", c_uint32),
        ("black_pixel", c_uint32),
        ("current_input_masks", c_uint32),
        ("width_in_pixels", c_uint16),
        ("height_in_pixels", c_uint16),
        ("width_in_millimeters", c_uint16),
        ("height_in_millimeters", c_uint16),
        ("min_installed_maps", c_uint16),
        ("max_installed_maps", c_uint16),
        ("root_visual", XcbVisualid),
        ("backing_stores", c_uint8),
        ("save_unders", c_uint8),
        ("root_depth", c_uint8),
        ("allowed_depths_len", c_uint8),
    )


class XcbScreenIterator(Structure):
    _fields_ = (("data", POINTER(XcbScreen)), ("rem", c_int), ("index", c_int))


class XcbSetup(Structure):
    _fields_ = (
        ("status", c_uint8),
        ("pad0", c_uint8),
        ("protocol_major_version", c_uint16),
        ("protocol_minor_version", c_uint16),
        ("length", c_uint16),
        ("release_number", c_uint32),
        ("resource_id_base", c_uint32),
        ("resource_id_mask", c_uint32),
        ("motion_buffer_size", c_uint32),
        ("vendor_len", c_uint16),
        ("maximum_request_length", c_uint16),
        ("roots_len", c_uint8),
        ("pixmap_formats_len", c_uint8),
        ("image_byte_order", c_uint8),
        ("bitmap_format_bit_order", c_uint8),
        ("bitmap_format_scanline_unit", c_uint8),
        ("bitmap_format_scanline_pad", c_uint8),
        ("min_keycode", XcbKeycode),
        ("max_keycode", XcbKeycode),
        ("pad1", c_uint8 * 4),
    )


# xproto: The core requests, in major number order.


class XcbGetGeometryReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        # The depth of the drawable (bits per pixel for the object).
        ("depth", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        # Root window of the screen containing `drawable`.
        ("root", XcbWindow),
        # The X coordinate of `drawable`. If `drawable` is a window,
        # the coordinate specifies the upper-left outer corner
        # relative to its parent's origin. If `drawable` is a pixmap,
        # the X coordinate is always 0.
        ("x", c_int16),
        # The Y coordinate of `drawable`. If `drawable` is a window,
        # the coordinate specifies the upper-left outer corner
        # relative to its parent's origin. If `drawable` is a pixmap,
        # the Y coordinate is always 0.
        ("y", c_int16),
        # The width of `drawable`.
        ("width", c_uint16),
        # The height of `drawable`.
        ("height", c_uint16),
        # The border width (in pixels).
        ("border_width", c_uint16),
        ("pad0", c_uint8 * 2),
    )


class XcbInternAtomReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("atom", XcbAtom),
    )


class XcbGetPropertyReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        # Specifies whether the data should be viewed as a list of
        # 8-bit, 16-bit, or 32-bit quantities. Possible values are
        # 8, 16, and 32. This information allows the X server to
        # correctly perform byte-swap operations as necessary.
        ("format_", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        # The actual type of the property (an atom).
        ("type", XcbAtom),
        # The number of bytes remaining to be read in the property if
        # a partial read was performed.
        ("bytes_after", c_uint32),
        # The length of value. You should use the corresponding
        # accessor instead of this field.
        ("value_len", c_uint32),
        ("pad0", c_uint8 * 12),
    )


class XcbGetImageReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("depth", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("visual", XcbVisualid),
        ("pad0", c_uint8 * 20),
    )


class XcbQueryExtensionReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        # Whether the extension is present on this X11 server.
        ("present", c_uint8),
        # The major opcode for requests.
        ("major_opcode", c_uint8),
        # The first event code, if any.
        ("first_event", c_uint8),
        # The first error code, if any.
        ("first_error", c_uint8),
    )


# Constants
# Since these are enums in XCB, they're interspersed with the types in
# the definitions, but I've put them together in deference to custom.

# XCB_NONE is the universal null resource or null atom parameter value
# for many core X requests.
XCB_NONE = XID(0)
XCB_ATOM_WINDOW = XcbAtom(33)
XCB_CONN_ERROR = 1
XCB_CONN_CLOSED_EXT_NOTSUPPORTED = 2
XCB_CONN_CLOSED_MEM_INSUFFICIENT = 3
XCB_CONN_CLOSED_REQ_LEN_EXCEED = 4
XCB_CONN_CLOSED_PARSE_ERR = 5
XCB_CONN_CLOSED_INVALID_SCREEN = 6
XCB_CONN_CLOSED_FDPASSING_FAILED = 7
XCB_IMAGE_FORMAT_Z_PIXMAP = 2
XCB_IMAGE_ORDER_LSB_FIRST = 0
XCB_VISUAL_CLASS_TRUE_COLOR = 4
XCB_VISUAL_CLASS_DIRECT_COLOR = 5

# I don't know of error descriptions for the XCB connection errors being accessible through a library (a la strerror),
# and the ones in xcb.h's comments aren't too great, so I wrote these.
XCB_CONN_ERRMSG = {
    XCB_CONN_ERROR: "connection lost or could not be established",
    XCB_CONN_CLOSED_EXT_NOTSUPPORTED: "extension not supported",
    XCB_CONN_CLOSED_MEM_INSUFFICIENT: "memory exhausted",
    XCB_CONN_CLOSED_REQ_LEN_EXCEED: "request length longer than server accepts",
    XCB_CONN_CLOSED_PARSE_ERR: "display is unset or invalid (check $DISPLAY)",
    XCB_CONN_CLOSED_INVALID_SCREEN: "server does not have a screen matching the requested display",
    XCB_CONN_CLOSED_FDPASSING_FAILED: "could not pass file descriptor",
}

# randr


class XcbRandrMode(XID):
    pass


class XcbRandrCrtc(XID):
    pass


class XcbRandrQueryVersionReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("major_version", c_uint32),
        ("minor_version", c_uint32),
        ("pad1", c_uint8 * 16),
    )


class XcbRandrGetScreenResourcesReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("timestamp", XcbTimestamp),
        ("config_timestamp", XcbTimestamp),
        ("num_crtcs", c_uint16),
        ("num_outputs", c_uint16),
        ("num_modes", c_uint16),
        ("names_len", c_uint16),
        ("pad1", c_uint8 * 8),
    )


class XcbRandrGetCrtcInfoReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("status", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("timestamp", XcbTimestamp),
        ("x", c_int16),
        ("y", c_int16),
        ("width", c_uint16),
        ("height", c_uint16),
        ("mode", XcbRandrMode),
        ("rotation", c_uint16),
        ("rotations", c_uint16),
        ("num_outputs", c_uint16),
        ("num_possible_outputs", c_uint16),
    )


class XcbRandrGetScreenResourcesCurrentReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("timestamp", XcbTimestamp),
        ("config_timestamp", XcbTimestamp),
        ("num_crtcs", c_uint16),
        ("num_outputs", c_uint16),
        ("num_modes", c_uint16),
        ("names_len", c_uint16),
        ("pad1", c_uint8 * 8),
    )


# The version of the spec that the client was written against.
XCB_RANDR_MAJOR_VERSION = 1
XCB_RANDR_MINOR_VERSION = 6


# render


class XcbRenderPictformat(XID):
    pass


class XcbRenderDirectformat(Structure):
    _fields_ = (
        ("red_shift", c_uint16),
        ("red_mask", c_uint16),
        ("green_shift", c_uint16),
        ("green_mask", c_uint16),
        ("blue_shift", c_uint16),
        ("blue_mask", c_uint16),
        ("alpha_shift", c_uint16),
        ("alpha_mask", c_uint16),
    )


class XcbRenderPictforminfo(Structure):
    _fields_ = (
        ("id", XcbRenderPictformat),
        ("type", c_uint8),
        ("depth", c_uint8),
        ("pad0", c_uint8 * 2),
        ("direct", XcbRenderDirectformat),
        ("colormap", XcbColormap),
    )


class XcbRenderPictvisual(Structure):
    _fields_ = (
        ("visual", XcbVisualid),
        ("format_", XcbRenderPictformat),
    )


class XcbRenderPictdepth(Structure):
    _fields_ = (
        ("depth", c_uint8),
        ("pad0", c_uint8),
        ("num_visuals", c_uint16),
        ("pad1", c_uint8 * 4),
    )


class XcbRenderPictdepthIterator(Structure):
    _fields_ = (("data", POINTER(XcbRenderPictdepth)), ("rem", c_int), ("index", c_int))


class XcbRenderPictscreen(Structure):
    _fields_ = (
        ("num_depths", c_uint32),
        ("fallback", XcbRenderPictformat),
    )


class XcbRenderPictscreenIterator(Structure):
    _fields_ = (("data", POINTER(XcbRenderPictscreen)), ("rem", c_int), ("index", c_int))


class XcbRenderQueryVersionReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("major_version", c_uint32),
        ("minor_version", c_uint32),
        ("pad1", c_uint8 * 16),
    )


class XcbRenderQueryPictFormatsReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("num_formats", c_uint32),
        ("num_screens", c_uint32),
        ("num_depths", c_uint32),
        ("num_visuals", c_uint32),
        ("num_subpixel", c_uint32),
        ("pad1", c_uint8 * 4),
    )


# The version of the spec that the client was written against.
XCB_RENDER_MAJOR_VERSION = 0
XCB_RENDER_MINOR_VERSION = 11


# xfixes


class XcbXfixesQueryVersionReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("major_version", c_uint32),
        ("minor_version", c_uint32),
        ("pad1", c_uint8 * 16),
    )


class XcbXfixesGetCursorImageReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("x", c_int16),
        ("y", c_int16),
        ("width", c_uint16),
        ("height", c_uint16),
        ("xhot", c_uint16),
        ("yhot", c_uint16),
        ("cursor_serial", c_uint32),
        ("pad1", c_uint8 * 8),
    )


# The version of the spec that the client was written against.
XCB_XFIXES_MAJOR_VERSION = 6
XCB_XFIXES_MINOR_VERSION = 0

# xcb-errors


class XcbErrorsContext(Structure):
    """A context for using libxcb-errors.

    Create a context with xcb_errors_context_new() and destroy it with xcb_errors_context_free(). Except for
    xcb_errors_context_free(), all functions in libxcb-errors are thread-safe and can be called from multiple threads
    at the same time, even on the same context.
    """


#### XCB libraries singleton


class LibContainer:
    """Container for XCB-related libraries.

    There is one instance exposed as the xcb.LIB global.

    You can access libxcb.so as xcb.LIB.xcb, libc as xcb.LIB.c, etc.

    This lazily-loads the libraries, so it's safe to create even if the library
    doesn't exist.  It will load and set up the libraries the first time that
    an attribute is accessed.  It also exposes an explicit load() method.

    Library accesses through this container return the ctypes CDLL object.
    There are no smart wrappers.  In other words, if you're accessing
    xcb.LIB.xcb.xcb_foo, then you need to handle the .reply() calls and such
    yourself.  If you're accessing the wrapper functions in the xcb module
    xcb.xcb_foo, then it will take care of that for you.
    """

    _EXPOSED_NAMES = frozenset(
        {"c", "xcb", "randr", "randr_id", "render", "render_id", "xfixes", "xfixes_id", "errors"}
    )

    def __init__(self) -> None:
        self._lock = Lock()
        self._initialized = False

    def reset(self) -> None:
        with self._lock:
            self._initialized = False
            for name in self._EXPOSED_NAMES:
                with suppress(AttributeError):
                    delattr(self, name)

    def __getattr__(self, name: str) -> CDLL:
        # In normal use, this will only be called once (for a library).  After that, all the names will be populated in
        # __dict__, and this fallback won't be used.
        if name in self._EXPOSED_NAMES:
            # This will set the attributes in self.__dict__, so __getattribute__ should now return them.
            self.load()
        # Go on to call object.__getattribute__.  This does the normal __dict__ lookup for us.  If it's for an
        # attribute we just created, then it will return it directly.  If it's for an attribute that genuinely doesn't
        # exist, it'll raise an AttributeError in the right format for the Python version (this changed slightly in
        # Python 3.10).
        return super().__getattribute__(name)

    def load(self) -> None:
        with self._lock:
            if self._initialized:
                # Something else initialized this object while we were waiting for the lock.
                return

            # We don't use the cached versions that ctypes.cdll exposes as attributes, since other libraries may be
            # doing their own things with these.

            # We use the libc that the current process has loaded, to make sure we get the right version of free().
            self.c = cdll.LoadLibrary(None)
            self.c.free.argtypes = [c_void_p]
            self.c.free.restype = None

            # In the future, most of the following could be auto-generated from the XML specs, like xcffib does.
            # Alternatively, we might define the functions to be initialized with a decorator on the functions that use
            # them.

            libxcb_so = ctypes.util.find_library("xcb")
            if libxcb_so is None:
                msg = "Library libxcb.so not found"
                raise ScreenShotError(msg)
            self.xcb = cdll.LoadLibrary(libxcb_so)

            # Ordered as <xcb/xcb.h>

            self.xcb.xcb_request_check.argtypes = [POINTER(XcbConnection), XcbVoidCookie]
            self.xcb.xcb_request_check.restype = POINTER(XcbGenericErrorStructure)
            self.xcb.xcb_discard_reply.argtypes = [POINTER(XcbConnection), c_uint]
            self.xcb.xcb_discard_reply.restype = None
            self.xcb.xcb_get_extension_data.argtypes = [POINTER(XcbConnection), POINTER(XcbExtension)]
            self.xcb.xcb_get_extension_data.restype = POINTER(XcbQueryExtensionReply)
            self.xcb.xcb_prefetch_extension_data.argtypes = [POINTER(XcbConnection), POINTER(XcbExtension)]
            self.xcb.xcb_prefetch_extension_data.restype = None

            self.xcb.xcb_get_setup.argtypes = [POINTER(XcbConnection)]
            self.xcb.xcb_get_setup.restype = POINTER(XcbSetup)
            self.xcb.xcb_connection_has_error.argtypes = [POINTER(XcbConnection)]
            self.xcb.xcb_connection_has_error.restype = c_int
            self.xcb.xcb_connect.argtypes = [c_char_p, POINTER(c_int)]
            self.xcb.xcb_connect.restype = POINTER(XcbConnection)
            self.xcb.xcb_disconnect.argtypes = [POINTER(XcbConnection)]
            self.xcb.xcb_disconnect.restype = None

            # Ordered as <xcb/xproto.h>

            self.xcb.xcb_depth_visuals.argtypes = [POINTER(XcbDepth)]
            self.xcb.xcb_depth_visuals.restype = POINTER(XcbVisualtype)
            self.xcb.xcb_depth_visuals_length.argtypes = [POINTER(XcbDepth)]
            self.xcb.xcb_depth_visuals_length.restype = c_int
            self.xcb.xcb_depth_next.argtypes = [POINTER(XcbDepthIterator)]
            self.xcb.xcb_depth_next.restype = None
            self.xcb.xcb_screen_allowed_depths_iterator.argtypes = [POINTER(XcbScreen)]
            self.xcb.xcb_screen_allowed_depths_iterator.restype = XcbDepthIterator
            self.xcb.xcb_screen_next.argtypes = [POINTER(XcbScreenIterator)]
            self.xcb.xcb_screen_next.restype = None
            self.xcb.xcb_setup_vendor.argtypes = [POINTER(XcbSetup)]
            self.xcb.xcb_setup_vendor.restype = POINTER(c_char)
            self.xcb.xcb_setup_vendor_length.argtypes = [POINTER(XcbSetup)]
            self.xcb.xcb_setup_vendor_length.restype = c_int
            self.xcb.xcb_setup_pixmap_formats.argtypes = [POINTER(XcbSetup)]
            self.xcb.xcb_setup_pixmap_formats.restype = POINTER(XcbFormat)
            self.xcb.xcb_setup_pixmap_formats_length.argtypes = [POINTER(XcbSetup)]
            self.xcb.xcb_setup_pixmap_formats_length.restype = c_int
            self.xcb.xcb_setup_roots_iterator.argtypes = [POINTER(XcbSetup)]
            self.xcb.xcb_setup_roots_iterator.restype = XcbScreenIterator
            initialize_xcb_typed_func(
                self.xcb, "xcb_get_geometry", [POINTER(XcbConnection), XcbDrawable], XcbGetGeometryReply
            )
            initialize_xcb_typed_func(
                self.xcb, "xcb_intern_atom", [POINTER(XcbConnection), c_uint8, c_uint16, c_char_p], XcbInternAtomReply
            )
            initialize_xcb_typed_func(
                self.xcb,
                "xcb_get_property",
                [POINTER(XcbConnection), c_uint8, XcbWindow, XcbAtom, XcbAtom, c_uint32, c_uint32],
                XcbGetPropertyReply,
            )
            self.xcb.xcb_get_property_value.argtypes = [POINTER(XcbGetPropertyReply)]
            self.xcb.xcb_get_property_value.restype = c_void_p
            self.xcb.xcb_get_property_value_length.argtypes = [POINTER(XcbGetPropertyReply)]
            self.xcb.xcb_get_property_value_length.restype = c_int
            initialize_xcb_typed_func(
                self.xcb,
                "xcb_get_image",
                [POINTER(XcbConnection), c_uint8, XcbDrawable, c_int16, c_int16, c_uint16, c_uint16, c_uint32],
                XcbGetImageReply,
            )
            self.xcb.xcb_get_image_data.argtypes = [POINTER(XcbGetImageReply)]
            self.xcb.xcb_get_image_data.restype = POINTER(c_uint8)
            self.xcb.xcb_get_image_data_length.argtypes = [POINTER(XcbGetImageReply)]
            self.xcb.xcb_get_image_data_length.restype = c_int
            initialize_xcb_void_func(self.xcb, "xcb_no_operation_checked", [POINTER(XcbConnection)])

            # Ordered as <xcb/randr.h>

            libxcb_randr_so = ctypes.util.find_library("xcb-randr")
            if libxcb_randr_so is None:
                msg = "Library libxcb-randr.so not found"
                raise ScreenShotError(msg)
            self.randr = cdll.LoadLibrary(libxcb_randr_so)
            self.randr_id = XcbExtension.in_dll(self.randr, "xcb_randr_id")
            initialize_xcb_typed_func(
                self.randr,
                "xcb_randr_query_version",
                [POINTER(XcbConnection), c_uint32, c_uint32],
                XcbRandrQueryVersionReply,
            )
            initialize_xcb_typed_func(
                self.randr,
                "xcb_randr_get_screen_resources",
                [POINTER(XcbConnection), XcbWindow],
                XcbRandrGetScreenResourcesReply,
            )
            self.randr.xcb_randr_get_screen_resources_crtcs.argtypes = [POINTER(XcbRandrGetScreenResourcesReply)]
            self.randr.xcb_randr_get_screen_resources_crtcs.restype = POINTER(XcbRandrCrtc)
            self.randr.xcb_randr_get_screen_resources_crtcs_length.argtypes = [POINTER(XcbRandrGetScreenResourcesReply)]
            self.randr.xcb_randr_get_screen_resources_crtcs_length.restype = c_int
            initialize_xcb_typed_func(
                self.randr,
                "xcb_randr_get_crtc_info",
                [POINTER(XcbConnection), XcbRandrCrtc, XcbTimestamp],
                XcbRandrGetCrtcInfoReply,
            )
            initialize_xcb_typed_func(
                self.randr,
                "xcb_randr_get_screen_resources_current",
                [POINTER(XcbConnection), XcbWindow],
                XcbRandrGetScreenResourcesCurrentReply,
            )
            self.randr.xcb_randr_get_screen_resources_current_crtcs.argtypes = [
                POINTER(XcbRandrGetScreenResourcesCurrentReply)
            ]
            self.randr.xcb_randr_get_screen_resources_current_crtcs.restype = POINTER(XcbRandrCrtc)
            self.randr.xcb_randr_get_screen_resources_current_crtcs_length.argtypes = [
                POINTER(XcbRandrGetScreenResourcesCurrentReply)
            ]
            self.randr.xcb_randr_get_screen_resources_current_crtcs_length.restype = c_int

            # Ordered as <xcb/render.h>

            libxcb_render_so = ctypes.util.find_library("xcb-render")
            if libxcb_render_so is None:
                msg = "Library libxcb-render.so not found"
                raise ScreenShotError(msg)
            self.render = cdll.LoadLibrary(libxcb_render_so)
            self.render_id = XcbExtension.in_dll(self.render, "xcb_render_id")

            self.render.xcb_render_pictdepth_visuals.argtypes = [POINTER(XcbRenderPictdepth)]
            self.render.xcb_render_pictdepth_visuals.restype = POINTER(XcbRenderPictvisual)
            self.render.xcb_render_pictdepth_visuals_length.argtypes = [POINTER(XcbRenderPictdepth)]
            self.render.xcb_render_pictdepth_visuals_length.restype = c_int
            self.render.xcb_render_pictdepth_next.argtypes = [POINTER(XcbRenderPictdepthIterator)]
            self.render.xcb_render_pictdepth_next.restype = None
            self.render.xcb_render_pictscreen_depths_iterator.argtypes = [POINTER(XcbRenderPictscreen)]
            self.render.xcb_render_pictscreen_depths_iterator.restype = XcbRenderPictdepthIterator
            self.render.xcb_render_pictscreen_next.argtypes = [POINTER(XcbRenderPictscreenIterator)]
            self.render.xcb_render_pictscreen_next.restype = None
            initialize_xcb_typed_func(
                self.render,
                "xcb_render_query_version",
                [POINTER(XcbConnection)],
                XcbRenderQueryVersionReply,
            )
            initialize_xcb_typed_func(
                self.render,
                "xcb_render_query_pict_formats",
                [POINTER(XcbConnection)],
                XcbRenderQueryPictFormatsReply,
            )
            self.render.xcb_render_query_pict_formats_formats.argtypes = [POINTER(XcbRenderQueryPictFormatsReply)]
            self.render.xcb_render_query_pict_formats_formats.restype = POINTER(XcbRenderPictforminfo)
            self.render.xcb_render_query_pict_formats_formats_length.argtypes = [
                POINTER(XcbRenderQueryPictFormatsReply)
            ]
            self.render.xcb_render_query_pict_formats_formats_length.restype = c_int
            self.render.xcb_render_query_pict_formats_screens_iterator.argtypes = [
                POINTER(XcbRenderQueryPictFormatsReply)
            ]
            self.render.xcb_render_query_pict_formats_screens_iterator.restype = XcbRenderPictscreenIterator

            # Ordered as <xcb/xfixes.h>

            libxcb_xfixes_so = ctypes.util.find_library("xcb-xfixes")
            if libxcb_xfixes_so is None:
                msg = "Library libxcb-xfixes.so not found"
                raise ScreenShotError(msg)
            self.xfixes = cdll.LoadLibrary(libxcb_xfixes_so)
            self.xfixes_id = XcbExtension.in_dll(self.xfixes, "xcb_xfixes_id")

            initialize_xcb_typed_func(
                self.xfixes,
                "xcb_xfixes_query_version",
                [POINTER(XcbConnection), c_uint32, c_uint32],
                XcbXfixesQueryVersionReply,
            )
            initialize_xcb_typed_func(
                self.xfixes,
                "xcb_xfixes_get_cursor_image",
                [POINTER(XcbConnection)],
                XcbXfixesGetCursorImageReply,
            )
            self.xfixes.xcb_xfixes_get_cursor_image_cursor_image.argtypes = [POINTER(XcbXfixesGetCursorImageReply)]
            self.xfixes.xcb_xfixes_get_cursor_image_cursor_image.restype = POINTER(c_uint32)
            self.xfixes.xcb_xfixes_get_cursor_image_cursor_image_length.argtypes = [
                POINTER(XcbXfixesGetCursorImageReply)
            ]
            self.xfixes.xcb_xfixes_get_cursor_image_cursor_image_length.restype = c_int

            # xcb_errors is an optional library, mostly only useful to developers.  We use the qualified .so name,
            # since it's subject to change incompatibly.
            try:
                self.errors = cdll.LoadLibrary("libxcb-errors.so.0")
            except Exception:  # noqa: BLE001
                self.errors = None
            else:
                self.errors.xcb_errors_context_new.argtypes = [
                    POINTER(XcbConnection),
                    POINTER(POINTER(XcbErrorsContext)),
                ]
                self.errors.xcb_errors_context_new.restype = c_int
                self.errors.xcb_errors_context_free.argtypes = [POINTER(XcbErrorsContext)]
                self.errors.xcb_errors_context_free.restype = None
                self.errors.xcb_errors_get_name_for_major_code.argtypes = [POINTER(XcbErrorsContext), c_uint8]
                self.errors.xcb_errors_get_name_for_major_code.restype = c_char_p
                self.errors.xcb_errors_get_name_for_minor_code.argtypes = [POINTER(XcbErrorsContext), c_uint8, c_uint16]
                self.errors.xcb_errors_get_name_for_minor_code.restype = c_char_p
                self.errors.xcb_errors_get_name_for_error.argtypes = [
                    POINTER(XcbErrorsContext),
                    c_uint8,
                    POINTER(c_char_p),
                ]
                self.errors.xcb_errors_get_name_for_error.restype = c_char_p

            self._initialized = True


LIB = LibContainer()


#### Protocol operations
#
# These follow a common pattern based on whether they return a value
# or not.  (Ruff won't let me demonstrate the pattern in a comment.)
#
# The docstrings are from the XML protocol specs, except for notes
# where this module defines an easy-to-use wrapper.
#
# In the future, these could be auto-generated from the XML specs,
# like xcffib does.


def xcb_get_geometry(c: XcbConnection, drawable: XcbDrawable) -> XcbGetGeometryReply:
    """Get current window geometry

    Gets the current geometry of the specified drawable (either
    `Window` or `Pixmap`).
    """
    return LIB.xcb.xcb_get_geometry(c, drawable).reply(c)


def xcb_intern_atom(
    c: XcbConnection, only_if_exists: c_uint8, name_len: c_uint16, name: c_char_p
) -> XcbInternAtomReply:
    """Get atom identifier by name

    Retrieves the identifier for the atom with the specified
    name. Atoms are used in protocols like EWMH, for example to store
    window titles (`_NET_WM_NAME` atom) as property of a window.

    If `only_if_exists` is 0, the atom will be created if it does not
    already exist.  If `only_if_exists` is 1, `XCB_NONE` will be
    returned if the atom does not yet exist.

    Python-MSS note: The `atom()` function defined in this module is
    easier to use.
    """
    return LIB.xcb.xcb_intern_atom(c, only_if_exists, name_len, name).reply(c)


def xcb_get_property(  # noqa: PLR0913
    c: XcbConnection,
    delete: c_uint8,
    window: XcbWindow,
    property_: XcbAtom,
    type_: XcbAtom,
    long_offset: c_uint32,
    long_length: c_uint32,
) -> XcbGetPropertyReply:
    """Gets a window property

    Gets the specified `property` from the specified
    `window`. Properties are for example the window title (`WM_NAME`)
    or its minimum size (`WM_NORMAL_HINTS`).  Protocols such as EWMH
    also use properties - for example EWMH defines the window title,
    encoded as UTF-8 string, in the `_NET_WM_NAME` property.

    Python-MSS note: For properties in UTF-8 format (most
    string-valued properties in the EWMH spec), the `get_utf8_prop()`
    function defined in this module is easier to use.

    """
    return LIB.xcb.xcb_get_property(c, delete, window, property_, type_, long_offset, long_length).reply(c)


def xcb_get_image(  # noqa: PLR0913
    c: XcbConnection,
    format_: c_uint8,
    drawable: XcbDrawable,
    x: c_int16,
    y: c_int16,
    width: c_uint16,
    height: c_uint16,
    plane_mask: c_uint32,
) -> XcbGetImageReply:
    return LIB.xcb.xcb_get_image(c, format_, drawable, x, y, width, height, plane_mask).reply(c)


# This is included as an example of a void operation.
def xcb_no_operation(c: XcbConnection) -> None:
    LIB.xcb.xcb_no_operation_checked(c).check(c)


def xcb_randr_get_crtc_info(
    c: XcbConnection, crtc: XcbRandrCrtc, config_timestamp: XcbTimestamp
) -> XcbRandrGetCrtcInfoReply:
    return LIB.randr.xcb_randr_get_crtc_info(c, crtc, config_timestamp).reply(c)


def xcb_randr_query_version(
    c: XcbConnection, major_version: c_uint32, minor_version: c_uint32
) -> XcbRandrQueryVersionReply:
    return LIB.randr.xcb_randr_query_version(c, major_version, minor_version).reply(c)


def xcb_randr_get_screen_resources(c: XcbConnection, window: XcbWindow) -> XcbRandrGetScreenResourcesReply:
    return LIB.randr.xcb_randr_get_screen_resources(c, window).reply(c)


def xcb_randr_get_screen_resources_current(
    c: XcbConnection, window: XcbWindow
) -> XcbRandrGetScreenResourcesCurrentReply:
    return LIB.randr.xcb_randr_get_screen_resources_current(c, window).reply(c)


def xcb_render_query_pict_formats(c: XcbConnection) -> XcbRenderQueryPictFormatsReply:
    return LIB.render.xcb_render_query_pict_formats(c).reply(c)


def xcb_render_query_version(c: XcbConnection) -> XcbRenderQueryVersionReply:
    return LIB.render.xcb_render_query_version(c).reply(c)


def xcb_xfixes_query_version(
    c: XcbConnection, client_major_version: c_uint32, client_minor_version: c_uint32
) -> XcbXfixesQueryVersionReply:
    return LIB.xfixes.xcb_xfixes_query_version(c, client_major_version, client_minor_version).reply(c)


def xcb_xfixes_get_cursor_image(c: XcbConnection) -> XcbXfixesGetCursorImageReply:
    return LIB.xfixes.xcb_xfixes_get_cursor_image(c).reply(c)


#### Trailing data accessors
#
# In X11, many replies have the header (the *Reply structures defined
# above), plus some variable-length data after it.  For instance,
# XcbScreen includes a list of XcbDepth structures.
#
# These mostly follow two patterns.
#
# For objects with a constant size, we get a pointer and length (count),
# cast to an array, and return the array contents.  (This doesn't involve
# copying any data.)
#
# For objects with a variable size, we use the XCB-provided iterator
# protocol to iterate over them, and return a Python list.  (This also
# doesn't copy any data, but does construct a list.)  To continue the
# example of how XcbScreen includes a list of XcbDepth structures: a
# full XcbDepth is variable-length because it has a variable number of
# visuals attached to it.
#
# These lists with variable element sizes follow a standard pattern:
#
# * There is an iterator class (such as XcbScreenIterator), based on
#   the type you're iterating over.  This defines a data pointer to
#   point to the current object, and a rem counter indicating the
#   remaining number of objects.
# * There is a function to advance the iterator (such as
#   xcb_screen_next), based on the type of iterator being advanced.
# * There is an initializer function (such as
#   xcb_setup_roots_iterator) that takes the container (XcbSetup), and
#   returns an iterator (XcbScreenIterator) pointing to the first object
#   in the list.  (This iterator is returned by value, so Python can
#   free it normally.)
#
# The returned structures are actually part of the allocation of the
# parent pointer: the POINTER(XcbScreen) objects point to objects that
# were allocated along with the XcbSetup that we got them from.  That
# means that it is very important that the XcbSetup not be freed until
# the pointers that point into it are freed.


### Iteration utility primitives


def iterate_xcb(iterator_factory: Callable, next_func: Callable, parent: Structure | _Pointer) -> Generator[Any]:
    # ctypes doesn't realize that the structure pointers we're
    # yielding are actually references into the parent structure's
    # allocation.  That means that the parent's finalizer can be
    # called, freeing it, while one of these is still live.
    #
    # One fix would be to put an extra reference to the parent struct
    # on the pointers we're returning.  However, that's not allowed by
    # ruff.  We use depends_on as an alternative.
    iterator = iterator_factory(parent)
    while iterator.rem != 0:
        current = iterator.data.contents
        depends_on(current, parent)
        yield current
        next_func(iterator)


def list_xcb(iterator_factory: Callable, next_func: Callable, parent: Structure | _Pointer) -> list:
    return list(iterate_xcb(iterator_factory, next_func, parent))


def array_xcb(pointer_func: Callable, length_func: Callable, parent: Structure | _Pointer) -> Array:
    pointer = pointer_func(parent)
    length = length_func(parent)
    array_ptr = cast(pointer, POINTER(pointer._type_ * length))
    array = array_ptr.contents
    depends_on(array, parent)
    return array


### Iteration implementations
#
# For constant-sized elements, these follow the same name as the XCB
# function.  The difference is that they return a size-aware ctypes
# Array instead of a pointer.
#
# For variable-sized elements, these omit the "_iterator" suffix,
# since they're not returning lists, not iterator structures.
#
# In the future, these could be auto-generated from the XML specs,
# like xcffib does.


# This is included as an easy test for this pattern.
def xcb_setup_vendor(r: XcbSetup) -> Array:
    return array_xcb(LIB.xcb.xcb_setup_vendor, LIB.xcb.xcb_setup_vendor_length, r)


def xcb_setup_roots(r: XcbSetup) -> list[_Pointer]:
    return list_xcb(LIB.xcb.xcb_setup_roots_iterator, LIB.xcb.xcb_screen_next, r)


def xcb_randr_get_screen_resources_crtcs(r: _Pointer) -> Array:
    return array_xcb(
        LIB.randr.xcb_randr_get_screen_resources_crtcs, LIB.randr.xcb_randr_get_screen_resources_crtcs_length, r
    )


def xcb_randr_get_screen_resources_current_crtcs(r: _Pointer) -> Array:
    return array_xcb(
        LIB.randr.xcb_randr_get_screen_resources_current_crtcs,
        LIB.randr.xcb_randr_get_screen_resources_current_crtcs_length,
        r,
    )


def xcb_setup_pixmap_formats(r: _Pointer) -> Array:
    return array_xcb(LIB.xcb.xcb_setup_pixmap_formats, LIB.xcb.xcb_setup_pixmap_formats_length, r)


def xcb_screen_allowed_depths(r: _Pointer) -> list[_Pointer]:
    return list_xcb(LIB.xcb.xcb_screen_allowed_depths_iterator, LIB.xcb.xcb_depth_next, r)


def xcb_depth_visuals(r: _Pointer) -> Array:
    return array_xcb(LIB.xcb.xcb_depth_visuals, LIB.xcb.xcb_depth_visuals_length, r)


def xcb_get_image_data(r: XcbGetImageReply) -> Array:
    return array_xcb(LIB.xcb.xcb_get_image_data, LIB.xcb.xcb_get_image_data_length, r)


def xcb_render_pictdepth_visuals(r: XcbRenderPictdepth) -> Array:
    return array_xcb(LIB.render.xcb_render_pictdepth_visuals, LIB.render.xcb_render_pictdepth_visuals_length, r)


def xcb_render_pictscreen_depths(r: XcbRenderPictscreen) -> list[_Pointer]:
    return list_xcb(LIB.render.xcb_render_pictscreen_depths_iterator, LIB.render.xcb_render_pictdepth_next, r)


def xcb_render_query_pict_formats_formats(r: XcbRenderQueryPictFormatsReply) -> Array:
    return array_xcb(
        LIB.render.xcb_render_query_pict_formats_formats, LIB.render.xcb_render_query_pict_formats_formats_length, r
    )


def xcb_render_query_pict_formats_screens(r: XcbRenderQueryPictFormatsReply) -> list[_Pointer]:
    return list_xcb(LIB.render.xcb_render_query_pict_formats_screens_iterator, LIB.render.xcb_render_pictscreen_next, r)


def xcb_xfixes_get_cursor_image_cursor_image(r: XcbXfixesGetCursorImageReply) -> Array:
    return array_xcb(
        LIB.xfixes.xcb_xfixes_get_cursor_image_cursor_image,
        LIB.xfixes.xcb_xfixes_get_cursor_image_cursor_image_length,
        r,
    )


#### Atoms and Properties

_ATOM_CACHE: dict[str, XcbAtom | None] = {}


def atom(xcb_conn: XcbConnection, name: str, *, only_if_exists: bool = True) -> XcbAtom | None:
    # We'll do our best to cache on the connection, since different
    # servers will have different values for the non-predefined atoms.
    # The connection object is unhashable, so all we can cache on is
    # its address.  An alternative would be to store the cache on the
    # connection object itself, but ruff doesn't like us adding
    # private properties.
    cache_key = (addressof(xcb_conn), name)
    if cache_key in _ATOM_CACHE:
        return _ATOM_CACHE[cache_key]
    # We don't bother locking the cache, since doubled work doesn't
    # hurt anything.

    # The X11 protocol spec, regarding InternAtom, says "The string
    # should use the ISO Latin-1 encoding."  The Xlib manual,
    # regarding XInternAtom, says that "If the atom name is not in the
    # Host Portable Character Encoding, the result is
    # implementation-dependent."  (HPCE is a subset of ASCII.)  Of
    # course, Xlib is free to impose additional restrictions.
    # However, the ICCCM manual says in a footnote, "The comment in
    # the protocol specification for InternAtom that ISO Latin-1
    # encoding should be used is in the nature of a convention; the
    # server treats the string as a byte sequence."  We use Latin-1
    # here, in deference to the convention.  Of course, we are only
    # using ASCII in practice, but we'll write the encoding correctly.
    name_encoded = name.encode("latin_1", errors="strict") if isinstance(name, str) else name

    resp = xcb_intern_atom(xcb_conn, int(only_if_exists), len(name_encoded), name_encoded)

    # We cache the negative response, even though the atom might be
    # created later in theory.  We also copy the atom to a fresh
    # object, so ctypes can free the response.
    new_atom = None if resp.atom.value == XCB_NONE.value else XcbAtom(resp.atom.value)
    _ATOM_CACHE[cache_key] = new_atom
    return new_atom


def get_utf8_prop(xcb_conn: XcbConnection, window: XcbWindow, prop_name: str) -> str:
    utf8_string_type = atom(xcb_conn, "UTF8_STRING")
    prop_atom = atom(xcb_conn, prop_name)
    resp = xcb_get_property(xcb_conn, 0, window, prop_atom, utf8_string_type, 0, 2**32 - 1)
    if resp.length == 0:
        return None
    bytes_arr = cast(LIB.xcb.xcb_get_property_value(resp), POINTER(c_uint8 * resp.value_len)).contents
    return bytes(bytes_arr).decode("utf_8")


#### Application code


def connect(display: str | bytes | None = None) -> tuple[XcbConnection, int]:
    if isinstance(display, str):
        display = display.encode("utf-8")

    pref_screen_num = c_int()
    conn_p = LIB.xcb.xcb_connect(display, pref_screen_num)

    # We still get a connection object even if the connection fails.
    conn_err = LIB.xcb.xcb_connection_has_error(conn_p)
    if conn_err != 0:
        msg = "Cannot connect to display: "
        conn_errmsg = XCB_CONN_ERRMSG.get(conn_err)
        if conn_errmsg:
            msg += conn_errmsg
        else:
            msg += f"error code {conn_err}"
        raise XError(msg)

    return conn_p.contents, pref_screen_num.value


def disconnect(conn: XcbConnection) -> None:
    conn_err = LIB.xcb.xcb_connection_has_error(conn)
    # XCB won't free its connection structures until we disconnect, even in the event of an error.
    LIB.xcb.xcb_disconnect(conn)
    if conn_err != 0:
        msg = "Connection to X server closed: "
        conn_errmsg = XCB_CONN_ERRMSG.get(conn_err)
        if conn_errmsg:
            msg += conn_errmsg
        else:
            msg += f"error code {conn_err}"
        raise XError(msg)


def main(target_name: Any = "emacs", *, verbose: bool = True) -> None:  # noqa: PLR0912, PLR0915
    import re  # noqa: PLC0415

    from PIL import Image  # noqa: PLC0415

    if not isinstance(target_name, re.Pattern):
        target_name = re.compile(re.escape(target_name))

    conn, pref_screen_num = connect()

    # This is just a ping, here to demonstrate and test a void-typed
    # call.
    xcb_no_operation(conn)

    # We need to have XCB initialize its internal cache about the
    # extensions.  We also want to make sure they're present and have
    # versions we can use.
    randr_ext_data = LIB.xcb.xcb_get_extension_data(conn, LIB.randr_id).contents
    if not randr_ext_data.present:
        msg = "RANDR extension not present on server"
        raise XError(msg)
    # We ask the server to give us anything up to 1.3.  If the server
    # only supports 1.2, then that's what it'll give us.
    randr_version_data = xcb_randr_query_version(conn, 1, 3)
    randr_version = (randr_version_data.major_version, randr_version_data.minor_version)
    if randr_version < (1, 3):
        # In production, we'll fall back to the non-Current function
        # in this case.
        msg = f"RANDR extension on server too old: {randr_version!r}"
        raise XError(msg)

    render_ext_data = LIB.xcb.xcb_get_extension_data(conn, LIB.render_id).contents
    if not render_ext_data.present:
        msg = "RENDER extension not present on server"
        raise XError(msg)
    render_version_data = xcb_render_query_version(conn)
    render_version = (render_version_data.major_version, render_version_data.minor_version)
    # 0.7 is the earliest I could find docs for, although the
    # spec implies that everything we've defined here was in 0.6.
    # Current as of this writing is 0.11.
    if render_version < (0, 7):
        msg = "RENDER extension on server too old: {render_version!r}"
        raise XError(msg)

    # Get the connection setup information that was included when we
    # connected.
    xcb_setup = LIB.xcb.xcb_get_setup(conn).contents
    vendor = xcb_setup_vendor(xcb_setup)
    if verbose:
        print("Vendor:", bytes(vendor).decode("ascii"))

    screens = xcb_setup_roots(xcb_setup)
    pref_screen = screens[pref_screen_num]
    root = pref_screen.root
    root_geom = xcb_get_geometry(conn, root)

    # Extra credit: target a single window
    #
    # This isn't a complete implementation.  _NET_CLIENT_LIST isn't
    # mandatory, but is very common.  Additionally, there are a few
    # ways the title can be set in ICCCM and EMWH.  See
    # https://x.org/releases/X11R7.6/doc/xorg-docs/specs/ICCCM/icccm.html#wm_name_property
    # and
    # https://specifications.freedesktop.org/wm/latest/ar01s05.html
    # That said, modern window managers set _NET_CLIENT_LIST and
    # _NET_WM_NAME.

    client_list_resp = xcb_get_property(conn, 0, root, atom(conn, "_NET_CLIENT_LIST"), XCB_ATOM_WINDOW, 0, 2**32 - 1)
    window_list = cast(LIB.xcb.xcb_get_property_value(client_list_resp), POINTER(XcbWindow))[: client_list_resp.length]
    if verbose:
        print([hex(x.value) for x in window_list])

    for w in window_list:
        if target_name.search(get_utf8_prop(conn, w, "_NET_WM_NAME")):
            drawable = w
            break
    else:
        msg = f"Couldn't find the window {target_name.pattern}"
        raise XError(msg)

    # Now, back to the show.

    # Get the monitor list.  (This code doesn't use it for anything
    # but printing a message, but I'll need it for MSS.)  The first
    # entry is the whole X11 screen that the drawable is on.  That's
    # the one that covers all the monitors.
    monitors = []
    monitors.append(
        {
            "left": root_geom.x,
            "top": root_geom.y,
            "width": root_geom.width,
            "height": root_geom.height,
        }
    )

    # After that, we have one for each monitor on that screen.
    screen_resources = xcb_randr_get_screen_resources_current(conn, drawable)
    crtcs = xcb_randr_get_screen_resources_current_crtcs(screen_resources)
    for crtc in crtcs:
        crtc_info = xcb_randr_get_crtc_info(conn, crtc, screen_resources.timestamp)
        if crtc_info.num_outputs == 0:
            continue
        monitors.append({"left": crtc_info.x, "top": crtc_info.y, "width": crtc_info.width, "height": crtc_info.height})

    # Extra credit would be to enumerate the virtual desktops;
    # see https://specifications.freedesktop.org/wm/latest/ar01s03.html

    if verbose:
        print(f"Detected monitors: {monitors!r}")

    drawable_geom = xcb_get_geometry(conn, drawable)
    capture_geom = (
        drawable_geom.x,
        drawable_geom.y,
        drawable_geom.width,
        drawable_geom.height,
    )

    all_planes = 0xFFFFFFFF  # XCB doesn't define AllPlanes
    img_reply = xcb_get_image(conn, XCB_IMAGE_FORMAT_Z_PIXMAP, drawable, *capture_geom, all_planes)

    # Extra credit: verify the visual is in the format that we expect.
    # (This should be read at setup time, and cached.)

    formats_arr = xcb_setup_pixmap_formats(xcb_setup)
    formats = {f.depth: f for f in formats_arr}
    depths = {}
    visuals = {}
    # We only bother with the visuals supported by the preferred
    # screen, since that's what we're capturing on.
    for xcb_depth in xcb_screen_allowed_depths(pref_screen):
        depth_visuals = xcb_depth_visuals(xcb_depth)
        depths[xcb_depth.depth] = {v.visual_id.value: v for v in depth_visuals}
        visuals.update(depths[xcb_depth.depth])

    expected_bpp = 32
    expected_red_mask = 0xFF0000
    expected_green_mask = 0x00FF00
    expected_blue_mask = 0x0000FF

    # Make sure our image is really in BGRx format.
    if not (
        xcb_setup.image_byte_order == XCB_IMAGE_ORDER_LSB_FIRST
        and formats[img_reply.depth].bits_per_pixel == expected_bpp
        and formats[img_reply.depth].scanline_pad == expected_bpp
        and visuals[img_reply.visual.value].class_ in {XCB_VISUAL_CLASS_TRUE_COLOR, XCB_VISUAL_CLASS_DIRECT_COLOR}
        and visuals[img_reply.visual.value].red_mask == expected_red_mask
        and visuals[img_reply.visual.value].green_mask == expected_green_mask
        and visuals[img_reply.visual.value].blue_mask == expected_blue_mask
    ):
        msg = "X11 server provided an image not in BGRx format"
        raise XError(msg)

    # Extra credit: determine if the returned data has an alpha
    # channel or not.  If there is not an alpha channel, then the
    # extra byte is typically 0, so shouldn't be used as alpha.  Core
    # X11 doesn't define alpha compositing; that's defined in the
    # XRender extension.  In practice, the ones with alpha are 32-bit
    # TrueColor visuals, and the ones without are 24-bit DirectColor
    # visuals.  But we'll check what XRender has to say.  (Again, this
    # should be read at setup time, and cached.)
    pict_formats_reply = xcb_render_query_pict_formats(conn)
    pict_format_by_id = {}
    for pictforminfo in xcb_render_query_pict_formats_formats(pict_formats_reply):
        pict_format_by_id[pictforminfo.id.value] = pictforminfo
    pict_format_by_visual = {}
    for pictscreen in xcb_render_query_pict_formats_screens(pict_formats_reply):
        for pictdepth in xcb_render_pictscreen_depths(pictscreen):
            for visualformat in xcb_render_pictdepth_visuals(pictdepth):
                pict_format_by_visual[visualformat.visual.value] = pict_format_by_id[visualformat.format_.value]

    expected_alpha_mask = 0xFF
    expected_alpha_shift = 24

    pictformat = pict_format_by_visual[img_reply.visual.value]
    has_alpha = (
        pictformat.direct.alpha_mask == expected_alpha_mask and pictformat.direct.alpha_shift == expected_alpha_shift
    )

    # Now, save the image.
    img_data_arr = xcb_get_image_data(img_reply)
    # The array in img_data_arr does obey the buffer protocol.  In
    # practice, though, I would wrap this in a memoryview before
    # returning it to the user.  Or, in the current version (which
    # doesn't support buffer reuse), a bytearray.
    img_data = memoryview(img_data_arr)

    # The user might handle it something like this.  For reasons I'm
    # unclear on, though, I haven't been able to find a case where
    # the RGBA version has its content overwritten.  (The RGB version
    # probably won't.)
    if has_alpha:
        img = Image.frombuffer("RGBA", (capture_geom[2], capture_geom[3]), img_data, "raw", "BGRA", 0, 1)
    else:
        img = Image.frombuffer("RGB", (capture_geom[2], capture_geom[3]), img_data, "raw", "BGRX", 0, 1)
    img.save("out.png")

    disconnect(conn)

    return img


if __name__ == "__main__":
    import sys

    main(sys.argv[1] if len(sys.argv) > 1 else "emacs")
