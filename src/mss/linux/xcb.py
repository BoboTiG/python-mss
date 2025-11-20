from __future__ import annotations

from ctypes import Structure, c_int, c_uint8, c_uint16, c_uint32

from . import xcbgen

# We import these just so they're re-exported to our users.
# ruff: noqa: F401
from .xcbgen import (
    RANDR_MAJOR_VERSION,
    RANDR_MINOR_VERSION,
    RENDER_MAJOR_VERSION,
    RENDER_MINOR_VERSION,
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
    RandrCrtc,
    RandrGetCrtcInfoReply,
    RandrGetScreenResourcesCurrentReply,
    RandrGetScreenResourcesReply,
    RandrMode,
    RandrModeInfo,
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
    xfixes_get_cursor_image,
    xfixes_get_cursor_image_cursor_image,
    xfixes_query_version,
)

# These are also here to re-export.
from .xcbhelpers import LIB, Connection, XError

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
        if conn_errmsg:
            msg += conn_errmsg
        else:
            msg += f"error code {conn_err}"
        raise XError(msg)

    return conn_p.contents, pref_screen_num.value


def disconnect(conn: Connection) -> None:
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
