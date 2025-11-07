from typing import Any

from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.models import Monitor
from mss.screenshot import ScreenShot

# FIXME: We can't currently import libxcb etc. straight from xcb,
# since it will update them when we call initialize, and we won't see
# the changes.  I'm going to change initialize's API to address that.
from . import xcb
from .xcb import (
    XCB_IMAGE_FORMAT_Z_PIXMAP,
    XCB_RANDR_MAJOR_VERSION,
    XCB_RANDR_MINOR_VERSION,
    XCB_XFIXES_MAJOR_VERSION,
    XCB_XFIXES_MINOR_VERSION,
    connect,
    disconnect,
    initialize,
    xcb_get_geometry,
    xcb_get_image,
    xcb_get_image_data,
    xcb_randr_get_crtc_info,
    xcb_randr_get_screen_resources,
    xcb_randr_get_screen_resources_crtcs,
    xcb_randr_get_screen_resources_current,
    xcb_randr_get_screen_resources_current_crtcs,
    xcb_randr_query_version,
    xcb_setup_roots,
    xcb_xfixes_get_cursor_image,
    xcb_xfixes_get_cursor_image_cursor_image,
    xcb_xfixes_query_version,
)

SUPPORTED_DEPTHS = {24, 32}
SUPPORTED_BYTES_PER_PIXEL = 32
ALL_PLANES = 0xFFFFFFFF  # XCB doesn't define AllPlanes


class MSS(MSSBase):
    """Multiple ScreenShots implementation for GNU/Linux.

    This implementation is based on XCB, using the GetImage request.
    It can optionally use some extensions:
    * RandR: Enumerate individual monitors' sizes.
    * XFixes: Including the cursor.
    """

    def __init__(self, /, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        display = kwargs.get("display", b"")
        if not display:
            display = None

        initialize()
        self.conn, pref_screen_num = connect(display)

        # Let XCB pre-populate its internal cache regarding the
        # extensions we might use, while we finish setup.
        xcb.libxcb.xcb_prefetch_extension_data(self.conn, xcb.xcb_randr_id)
        xcb.libxcb.xcb_prefetch_extension_data(self.conn, xcb.xcb_xfixes_id)

        # Get the connection setup information that was included when we
        # connected.
        xcb_setup = xcb.libxcb.xcb_get_setup(self.conn).contents
        screens = xcb_setup_roots(xcb_setup)
        pref_screen = screens[pref_screen_num]
        self.root = self.drawable = pref_screen.root

        # We don't probe the XFixes presence or version until we need it.
        self._xfixes_ready = None

    def close(self) -> None:
        if self.conn is not None:
            disconnect(self.conn)
        self.conn = None

    def _monitors_impl(self) -> None:
        """Get positions of monitors. It will populate self._monitors."""

        # The first entry is the whole X11 screen that the root is
        # on.  That's the one that covers all the monitors.
        root_geom = xcb_get_geometry(self.conn, self.root)
        self._monitors.append(
            {
                "left": root_geom.x,
                "top": root_geom.y,
                "width": root_geom.width,
                "height": root_geom.height,
            }
        )

        # After that, we have one for each monitor on that X11 screen.
        # For decades, that's been handled by Xrandr.  We don't
        # presently try to work with Xinerama.  So, we're going to
        # check the different outputs, according to Xrandr.  If that
        # fails, we'll just leave the one root covering everything.

        # Make sure we have the Xrandr extension we need.  This will
        # query the cache that we started populating in __init__.
        randr_ext_data = xcb.libxcb.xcb_get_extension_data(self.conn, xcb.xcb_randr_id).contents
        if not randr_ext_data.present:
            return

        # We ask the server to give us anything up to the version we
        # support (i.e., what we expect the reply structs to look
        # like).  If the server only supports 1.2, then that's what
        # it'll give us, and we're ok with that, but we also use a
        # faster path if the server implements at least 1.3.
        randr_version_data = xcb_randr_query_version(self.conn, XCB_RANDR_MAJOR_VERSION, XCB_RANDR_MINOR_VERSION)
        randr_version = (randr_version_data.major_version, randr_version_data.minor_version)
        if randr_version < (1, 2):
            return

        # Check to see if we have the xcb_randr_get_screen_resources_current
        # function in libxcb-randr, and that the server supports it.
        if hasattr(xcb.randr, "xcb_randr_get_screen_resources_current") and randr_version >= (1, 3):
            screen_resources = xcb_randr_get_screen_resources_current(self.conn, self.drawable)
            crtcs = xcb_randr_get_screen_resources_current_crtcs(screen_resources)
        else:
            # Either the client or the server doesn't support the _current
            # form.  That's ok; we'll use the old function, which forces
            # a new query to the physical monitors.
            screen_resources = xcb_randr_get_screen_resources(self.conn, self.drawable)
            crtcs = xcb_randr_get_screen_resources_crtcs(screen_resources)

        for crtc in crtcs:
            crtc_info = xcb_randr_get_crtc_info(self.conn, crtc, screen_resources.timestamp)
            if crtc_info.num_outputs == 0:
                continue
            self._monitors.append(
                {"left": crtc_info.x, "top": crtc_info.y, "width": crtc_info.width, "height": crtc_info.height}
            )

        # Extra credit would be to enumerate the virtual desktops; see
        # https://specifications.freedesktop.org/wm/latest/ar01s03.html
        # But I don't know how widely-used that style is.

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""

        img_reply = xcb_get_image(
            self.conn,
            XCB_IMAGE_FORMAT_Z_PIXMAP,
            self.drawable,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            ALL_PLANES,
        )

        # Now, save the image.  This is a reference into the img_reply
        # structure.
        img_data_arr = xcb_get_image_data(img_reply)
        # Copy this into a new bytearray, so that it will persist after
        # we clear the image structure.
        img_data = bytearray(img_data_arr)

        # FIXME In xcb.main(), there's a more complete implementation
        # of checking the bit depth.  This includes checking the
        # visual type, byte order, and also determines whether the
        # alpha channel is real or just padding.
        #
        # In XCB, we don't get the bits per pixel with the image; it's
        # actually part of the visual data.  (Xlib puts the necessary
        # visual data in the image structure automatically.)  So for
        # now, we just check the depth, until I get around to checking
        # the full visual.
        if img_reply.depth not in SUPPORTED_DEPTHS:
            msg = f"[GetImage] depth value not implemented: {img_reply.depth}."
            raise ScreenShotError(msg)

        return self.cls_image(img_data, monitor)

    def _cursor_impl_check_xfixes(self) -> bool:
        xfixes_ext_data = xcb.libxcb.xcb_get_extension_data(self.conn, xcb.xcb_xfixes_id).contents
        if not xfixes_ext_data.present:
            return False

        reply = xcb_xfixes_query_version(self.conn, XCB_XFIXES_MAJOR_VERSION, XCB_XFIXES_MINOR_VERSION)
        # We can work with 2.0 and later, but not sure about the
        # actual minimum version we can use.  That's ok; everything
        # these days is much more modern.
        return not (reply.major_version, reply.minor_version) < (2, 0)

    def _cursor_impl(self) -> ScreenShot:
        """Retrieve all cursor data. Pixels have to be RGBx."""

        if self._xfixes_ready is None:
            self._xfixes_ready = self._cursor_impl_check_xfixes()
        if not self._xfixes_ready:
            msg = "Server does not have XFixes, or the version is too old."
            raise ScreenShotError(msg)

        cursor_img = xcb_xfixes_get_cursor_image(self.conn)
        region = {
            "left": cursor_img.x - cursor_img.xhot,
            "top": cursor_img.y - cursor_img.yhot,
            "width": cursor_img.width,
            "height": cursor_img.height,
        }

        data_arr = xcb_xfixes_get_cursor_image_cursor_image(cursor_img)
        data = bytearray(data_arr)
        # We don't need to do the same array slice-and-dice work as
        # the Xlib-based implementation: Xlib has an unfortunate
        # historical accident that makes it have to return the cursor
        # image in a different format.

        return self.cls_image(data, region)
