from __future__ import annotations

import contextlib
from ctypes import _Pointer, addressof, c_int
from typing import Literal, overload

from mss.linux import xcbgen

# We import these just so they're re-exported to our users.
# ruff: noqa: F401
from mss.linux.xcbgen import (
    RANDR_MAJOR_VERSION,
    RANDR_MINOR_VERSION,
    RENDER_MAJOR_VERSION,
    RENDER_MINOR_VERSION,
    SHM_MAJOR_VERSION,
    SHM_MINOR_VERSION,
    XFIXES_MAJOR_VERSION,
    XFIXES_MINOR_VERSION,
    Atom,
    BackingStore,
    Colormap,
    Depth,
    DepthIterator,
    Drawable,
    Format,
    GetGeometryReply,
    GetImageReply,
    GetPropertyReply,
    ImageFormat,
    ImageOrder,
    Keycode,
    Pixmap,
    RandrConnection,
    RandrCrtc,
    RandrGetCrtcInfoReply,
    RandrGetMonitorsReply,
    RandrGetOutputInfoReply,
    RandrGetOutputPrimaryReply,
    RandrGetOutputPropertyReply,
    RandrGetScreenResourcesCurrentReply,
    RandrGetScreenResourcesReply,
    RandrMode,
    RandrModeInfo,
    RandrMonitorInfo,
    RandrMonitorInfoIterator,
    RandrOutput,
    RandrQueryVersionReply,
    RandrSetConfig,
    RenderDirectformat,
    RenderPictdepth,
    RenderPictdepthIterator,
    RenderPictformat,
    RenderPictforminfo,
    RenderPictscreen,
    RenderPictscreenIterator,
    RenderPictType,
    RenderPictvisual,
    RenderQueryPictFormatsReply,
    RenderQueryVersionReply,
    RenderSubPixel,
    Screen,
    ScreenIterator,
    Setup,
    SetupIterator,
    ShmCreateSegmentReply,
    ShmGetImageReply,
    ShmQueryVersionReply,
    ShmSeg,
    Timestamp,
    VisualClass,
    Visualid,
    Visualtype,
    Window,
    XfixesGetCursorImageReply,
    XfixesQueryVersionReply,
    depth_visuals,
    get_geometry,
    get_image,
    get_image_data,
    get_property,
    get_property_value,
    no_operation,
    randr_get_crtc_info,
    randr_get_crtc_info_outputs,
    randr_get_crtc_info_possible,
    randr_get_monitors,
    randr_get_monitors_monitors,
    randr_get_output_info,
    randr_get_output_info_clones,
    randr_get_output_info_crtcs,
    randr_get_output_info_modes,
    randr_get_output_info_name,
    randr_get_output_primary,
    randr_get_output_property,
    randr_get_output_property_data,
    randr_get_screen_resources,
    randr_get_screen_resources_crtcs,
    randr_get_screen_resources_current,
    randr_get_screen_resources_current_crtcs,
    randr_get_screen_resources_current_modes,
    randr_get_screen_resources_current_names,
    randr_get_screen_resources_current_outputs,
    randr_get_screen_resources_modes,
    randr_get_screen_resources_names,
    randr_get_screen_resources_outputs,
    randr_monitor_info_outputs,
    randr_query_version,
    render_pictdepth_visuals,
    render_pictscreen_depths,
    render_query_pict_formats,
    render_query_pict_formats_formats,
    render_query_pict_formats_screens,
    render_query_pict_formats_subpixels,
    render_query_version,
    screen_allowed_depths,
    setup_pixmap_formats,
    setup_roots,
    setup_vendor,
    shm_attach_fd,
    shm_create_segment,
    shm_create_segment_reply_fds,
    shm_detach,
    shm_get_image,
    shm_query_version,
    xfixes_get_cursor_image,
    xfixes_get_cursor_image_cursor_image,
    xfixes_query_version,
)

# These are also here to re-export.
from mss.linux.xcbhelpers import LIB, XID, Connection, InternAtomReply, QueryExtensionReply, XcbExtension, XError

XCB_CONN_ERROR = 1
XCB_CONN_CLOSED_EXT_NOTSUPPORTED = 2
XCB_CONN_CLOSED_MEM_INSUFFICIENT = 3
XCB_CONN_CLOSED_REQ_LEN_EXCEED = 4
XCB_CONN_CLOSED_PARSE_ERR = 5
XCB_CONN_CLOSED_INVALID_SCREEN = 6
XCB_CONN_CLOSED_FDPASSING_FAILED = 7

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


#### High-level XCB function wrappers

# XCB_NONE is the universal null resource or null atom parameter value for many core X requests
XCB_NONE = Atom(0)

# Some atoms are defined by the spec, to avoid apps having to look them up.  It's fine to look them up anyway.
_PREDEFINED_ATOMS = {
    "PRIMARY": Atom(1),
    "SECONDARY": Atom(2),
    "ARC": Atom(3),
    "ATOM": Atom(4),
    "BITMAP": Atom(5),
    "CARDINAL": Atom(6),
    "COLORMAP": Atom(7),
    "CURSOR": Atom(8),
    "CUT_BUFFER0": Atom(9),
    "CUT_BUFFER1": Atom(10),
    "CUT_BUFFER2": Atom(11),
    "CUT_BUFFER3": Atom(12),
    "CUT_BUFFER4": Atom(13),
    "CUT_BUFFER5": Atom(14),
    "CUT_BUFFER6": Atom(15),
    "CUT_BUFFER7": Atom(16),
    "DRAWABLE": Atom(17),
    "FONT": Atom(18),
    "INTEGER": Atom(19),
    "PIXMAP": Atom(20),
    "POINT": Atom(21),
    "RECTANGLE": Atom(22),
    "RESOURCE_MANAGER": Atom(23),
    "RGB_COLOR_MAP": Atom(24),
    "RGB_BEST_MAP": Atom(25),
    "RGB_BLUE_MAP": Atom(26),
    "RGB_DEFAULT_MAP": Atom(27),
    "RGB_GRAY_MAP": Atom(28),
    "RGB_GREEN_MAP": Atom(29),
    "RGB_RED_MAP": Atom(30),
    "STRING": Atom(31),
    "VISUALID": Atom(32),
    "WINDOW": Atom(33),
    "WM_COMMAND": Atom(34),
    "WM_HINTS": Atom(35),
    "WM_CLIENT_MACHINE": Atom(36),
    "WM_ICON_NAME": Atom(37),
    "WM_ICON_SIZE": Atom(38),
    "WM_NAME": Atom(39),
    "WM_NORMAL_HINTS": Atom(40),
    "WM_SIZE_HINTS": Atom(41),
    "WM_ZOOM_HINTS": Atom(42),
    "MIN_SPACE": Atom(43),
    "NORM_SPACE": Atom(44),
    "MAX_SPACE": Atom(45),
    "END_SPACE": Atom(46),
    "SUPERSCRIPT_X": Atom(47),
    "SUPERSCRIPT_Y": Atom(48),
    "SUBSCRIPT_X": Atom(49),
    "SUBSCRIPT_Y": Atom(50),
    "UNDERLINE_POSITION": Atom(51),
    "UNDERLINE_THICKNESS": Atom(52),
    "STRIKEOUT_ASCENT": Atom(53),
    "STRIKEOUT_DESCENT": Atom(54),
    "ITALIC_ANGLE": Atom(55),
    "X_HEIGHT": Atom(56),
    "QUAD_WIDTH": Atom(57),
    "WEIGHT": Atom(58),
    "POINT_SIZE": Atom(59),
    "RESOLUTION": Atom(60),
    "COPYRIGHT": Atom(61),
    "NOTICE": Atom(62),
    "FONT_NAME": Atom(63),
    "FAMILY_NAME": Atom(64),
    "FULL_NAME": Atom(65),
    "CAP_HEIGHT": Atom(66),
    "WM_CLASS": Atom(67),
    "WM_TRANSIENT_FOR": Atom(68),
}

# The atom cache needs to be per-connection. Rather than keying on a (connection, name) tuple, we use a two-level
# cache keyed by the integer address of the underlying XCB connection (see ctypes.addressof in intern_atom).
_ATOM_CACHE: dict[int, dict[str, Atom]] = {}


@overload
def intern_atom(
    xcb_conn: Connection | _Pointer[Connection],
    name: str,
    *,
    only_if_exists: Literal[False] = False,
) -> Atom: ...
@overload
def intern_atom(
    xcb_conn: Connection | _Pointer[Connection],
    name: str,
    *,
    only_if_exists: Literal[True] = True,
) -> Atom | None: ...
@overload
def intern_atom(
    xcb_conn: Connection | _Pointer[Connection],
    name: str,
    *,
    only_if_exists: bool,
) -> Atom | None: ...


def intern_atom(
    xcb_conn: Connection | _Pointer[Connection],
    name: str,
    *,
    only_if_exists: bool = False,
) -> Atom | None:
    if name in _PREDEFINED_ATOMS:
        return _PREDEFINED_ATOMS[name]

    if isinstance(xcb_conn, _Pointer):
        # Dereference the pointer before using the cache.
        xcb_conn = xcb_conn.contents
    cache_key = addressof(xcb_conn)
    if cache_key not in _ATOM_CACHE:
        # This can happen if the connection was closed and its cache cleared, but some code still has a reference to
        # the connection object.  We could re-create the cache entry, but it's safer to just fail instead of silently
        # allowing lookups to succeed when they shouldn't.
        msg = "Connection to X server is closed"
        raise XError(msg)
    if name in _ATOM_CACHE[cache_key]:
        return _ATOM_CACHE[cache_key][name]

    # Atom names are required to be Latin-1, per the X protocol spec, although anything that's not in the XPCS (a
    # subset of ASCII) is vendor-defined.
    name_encoded = name.encode("latin_1", errors="strict")
    cookie = LIB.xcb.xcb_intern_atom(xcb_conn, 1 if only_if_exists else 0, len(name_encoded), name_encoded)
    atom_as_xid = cookie.reply(xcb_conn).atom
    if atom_as_xid.value == 0:
        if not only_if_exists:
            # This shouldn't be possible.  We at least need to have a path for the type-checker to be happy, though.
            msg = f"X server failed to intern atom '{name}'"
            raise XError(msg)
        # We don't do negative caching, since any app might intern the atom at any time.
        return None
    atom = Atom(atom_as_xid.value)
    _ATOM_CACHE[cache_key][name] = atom
    return atom


def get_extension_data(
    xcb_conn: Connection | _Pointer[Connection], ext: XcbExtension | _Pointer[XcbExtension]
) -> QueryExtensionReply:
    """Get extension data for the given extension.

    Returns the extension data, which includes whether the extension is present
    and its opcode information.
    """
    reply_p = LIB.xcb.xcb_get_extension_data(xcb_conn, ext)
    return reply_p.contents


def prefetch_extension_data(
    xcb_conn: Connection | _Pointer[Connection], ext: XcbExtension | _Pointer[XcbExtension]
) -> None:
    """Prefetch extension data for the given extension.

    This is a performance hint to XCB to fetch the extension data
    asynchronously.
    """
    LIB.xcb.xcb_prefetch_extension_data(xcb_conn, ext)


def generate_id(xcb_conn: Connection | _Pointer[Connection]) -> XID:
    """Generate a new unique X resource ID.

    Returns an XID that can be used to create new X resources.
    """
    return LIB.xcb.xcb_generate_id(xcb_conn)


def get_setup(xcb_conn: Connection | _Pointer[Connection]) -> Setup:
    """Get the connection setup information.

    Returns the setup structure containing information about the X server,
    including available screens, pixmap formats, etc.
    """
    setup_p = LIB.xcb.xcb_get_setup(xcb_conn)
    return setup_p.contents


# Connection management


def initialize() -> None:
    LIB.initialize(callbacks=[xcbgen.initialize])


def connect(display: str | bytes | None = None) -> tuple[Connection, int]:
    if isinstance(display, str):
        display = display.encode("utf-8")

    initialize()
    pref_screen_num = c_int()
    conn_p = LIB.xcb.xcb_connect(display, pref_screen_num)

    # We still get a connection object even if the connection fails.
    conn_err = LIB.xcb.xcb_connection_has_error(conn_p)
    if conn_err != 0:
        # XCB won't free its connection structures until we disconnect, even in the event of an error.
        LIB.xcb.xcb_disconnect(conn_p)
        msg = "Cannot connect to display: "
        conn_errmsg = XCB_CONN_ERRMSG.get(conn_err)
        msg += conn_errmsg or f"error code {conn_err}"
        raise XError(msg)

    # Prefetch extension data for all extensions we support to populate XCB's internal cache.
    prefetch_extension_data(conn_p, LIB.randr_id)
    prefetch_extension_data(conn_p, LIB.render_id)
    prefetch_extension_data(conn_p, LIB.shm_id)
    prefetch_extension_data(conn_p, LIB.xfixes_id)

    _ATOM_CACHE[addressof(conn_p.contents)] = {}

    return conn_p.contents, pref_screen_num.value


def disconnect(xcb_conn: Connection | _Pointer[Connection]) -> None:
    if isinstance(xcb_conn, _Pointer):
        # Dereference the pointer before using the cache.
        xcb_conn = xcb_conn.contents

    # The cache might already be cleared if the connection had an error, or if disconnect was called multiple times.
    with contextlib.suppress(KeyError):
        del _ATOM_CACHE[addressof(xcb_conn)]

    conn_err = LIB.xcb.xcb_connection_has_error(xcb_conn)
    # XCB won't free its connection structures until we disconnect, even in the event of an error.
    LIB.xcb.xcb_disconnect(xcb_conn)
    if conn_err != 0:
        msg = "Connection to X server closed: "
        conn_errmsg = XCB_CONN_ERRMSG.get(conn_err)
        msg += conn_errmsg or f"error code {conn_err}"
        raise XError(msg)
