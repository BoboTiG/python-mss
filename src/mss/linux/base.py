from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from mss.base import MSSImplementation
from mss.exception import ScreenShotError
from mss.linux import xcb
from mss.linux.xcb import LIB
from mss.screenshot import ScreenShot
from mss.tools import parse_edid

if TYPE_CHECKING:
    from ctypes import Array

    from mss.models import Monitor, Monitors

__all__ = ()

SUPPORTED_DEPTHS = {24, 32}
SUPPORTED_BITS_PER_PIXEL = 32
SUPPORTED_RED_MASK = 0xFF0000
SUPPORTED_GREEN_MASK = 0x00FF00
SUPPORTED_BLUE_MASK = 0x0000FF
ALL_PLANES = 0xFFFFFFFF  # XCB doesn't define AllPlanes


class MSSImplXCBBase(MSSImplementation):
    """Base class for XCB-based screenshot implementations.

    Provides common XCB initialization and monitor detection logic that can be
    shared across different XCB screenshot methods (``XGetImage``,
    ``XShmGetImage``, ``XComposite``, etc.).

    :param display: Optional keyword argument.
        Specifies an X11 display string to connect to.  The default is
        taken from the environment variable :envvar:`DISPLAY`.
    :type display: str | bytes | None

    .. seealso::
        :py:class:`mss.MSS`
            Lists other parameters.
    """

    def __init__(self, *, display: str | bytes | None = None, with_cursor: bool = False) -> None:  # noqa: PLR0912
        super().__init__(with_cursor=with_cursor)

        if not display:
            display = None
        elif isinstance(display, str):
            display = display.encode("utf-8")

        self.conn: xcb.Connection | None
        self.conn, pref_screen_num = xcb.connect(display)

        # Get the connection setup information that was included when we connected.
        xcb_setup = xcb.get_setup(self.conn)
        screens = xcb.setup_roots(xcb_setup)
        # pref_screen_num is the screen object corresponding to the screen number, e.g., 1 if DISPLAY=":0.1".  It's
        # almost always the only screen (screen 0); nobody uses separate screens (in the X sense) anymore.
        self.pref_screen = screens[pref_screen_num]
        self.root = self.drawable = self.pref_screen.root

        # We don't probe the XFixes presence or version until we need it.
        self._xfixes_ready: bool | None = None

        # Probe the visuals (and related information), and make sure that our drawable is in an acceptable format.
        # These iterations and tests don't involve any traffic with the server; it's all stuff that was included in
        # the connection setup.  Effectively all modern setups will be acceptable, but we verify to be sure.

        # Currently, we assume that the drawable we're capturing is the root; when we add single-window capture,
        # we'll have to ask the server for its depth and visual.
        assert self.root == self.drawable  # noqa: S101
        self.drawable_depth = self.pref_screen.root_depth
        self.drawable_visual_id = self.pref_screen.root_visual
        # Server image byte order
        if xcb_setup.image_byte_order != xcb.ImageOrder.LSBFirst:
            msg = "Only X11 servers using LSB-First images are supported."
            raise ScreenShotError(msg)
        # Depth
        if self.drawable_depth not in SUPPORTED_DEPTHS:
            msg = f"Only screens of color depth 24 or 32 are supported, not {self.drawable_depth}"
            raise ScreenShotError(msg)
        # Format (i.e., bpp, padding)
        for format_ in xcb.setup_pixmap_formats(xcb_setup):
            if format_.depth == self.drawable_depth:
                break
        else:
            msg = f"Internal error: drawable's depth {self.drawable_depth} not found in screen's supported formats"
            raise ScreenShotError(msg)
        drawable_format = format_
        if drawable_format.bits_per_pixel != SUPPORTED_BITS_PER_PIXEL:
            msg = (
                f"Only screens at 32 bpp (regardless of color depth) are supported; "
                f"got {drawable_format.bits_per_pixel} bpp"
            )
            raise ScreenShotError(msg)
        if drawable_format.scanline_pad != SUPPORTED_BITS_PER_PIXEL:
            # To clarify the padding: the scanline_pad is the multiple that the scanline gets padded to.  If there
            # is no padding, then it will be the same as one pixel's size.
            msg = "Screens with scanline padding are not supported"
            raise ScreenShotError(msg)
        # Visual, the interpretation of pixels (like indexed, grayscale, etc).  (Visuals are arranged by depth, so
        # we iterate over the depths first.)
        for xcb_depth in xcb.screen_allowed_depths(self.pref_screen):
            if xcb_depth.depth == self.drawable_depth:
                break
        else:
            msg = "Internal error: drawable's depth not found in screen's supported depths"
            raise ScreenShotError(msg)
        for visual_info in xcb.depth_visuals(xcb_depth):
            if visual_info.visual_id == self.drawable_visual_id:
                break
        else:
            msg = "Internal error: drawable's visual not found in screen's supported visuals"
            raise ScreenShotError(msg)
        if visual_info.class_ not in {xcb.VisualClass.TrueColor, xcb.VisualClass.DirectColor}:
            msg = "Only TrueColor and DirectColor visuals are supported"
            raise ScreenShotError(msg)
        if (
            visual_info.red_mask != SUPPORTED_RED_MASK
            or visual_info.green_mask != SUPPORTED_GREEN_MASK
            or visual_info.blue_mask != SUPPORTED_BLUE_MASK
        ):
            # There are two ways to phrase this layout: BGRx accounts for the byte order, while xRGB implies the
            # native word order.  Since we return the data as a byte array, we use the former.  By the time we get
            # to this point, we've already checked the endianness and depth, so this is pretty much never going to
            # happen anyway.
            msg = "Only visuals with BGRx ordering are supported"
            raise ScreenShotError(msg)

    def close(self) -> None:
        """Close the XCB connection."""
        if self.conn is not None:
            xcb.disconnect(self.conn)
        self.conn = None

    def monitors(self) -> Monitors:
        """Populate monitor geometry information.

        Detects and returns monitor rectangles. The first entry
        represents the entire X11 root screen; subsequent entries,
        when available, represent individual monitors reported by
        XRandR.
        """
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        monitors = []

        monitors.append(self._root_monitor())

        randr_version = self._randr_get_version()
        if randr_version is None or randr_version < (1, 2):
            return monitors

        # XRandR terminology (very abridged, but enough for this code):
        # - X screen / framebuffer: the overall drawable area for this root.
        # - CRTC: a display controller that scans out a rectangular region of the X screen.  A CRTC with zero
        #   outputs is inactive.  A CRTC may drive multiple outputs in clone/mirroring mode.
        # - Output: a physical connector (e.g. "HDMI-1", "DP-1").  The RandR "connection" state (connected vs
        #   disconnected) is separate from whether the output is currently driven by a CRTC.
        # - Monitor (RandR 1.5+): a logical rectangle presented to clients.  Monitors may be client-defined (useful
        #   for tiled displays) and are the closest match to what MSS wants.
        #
        # This implementation prefers RandR 1.5+ Monitors when available; otherwise it falls back to enumerating
        # active CRTCs.

        primary_output = self._randr_get_primary_output(randr_version)
        edid_atom = self._randr_get_edid_atom()

        if randr_version >= (1, 5):
            monitors += self._monitors_from_randr_monitors(primary_output, edid_atom)
        else:
            monitors += self._monitors_from_randr_crtcs(randr_version, primary_output, edid_atom)

        return monitors

    def _root_monitor(self) -> Monitor:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        root_geom = xcb.get_geometry(self.conn, self.root)
        return {
            "left": root_geom.x,
            "top": root_geom.y,
            "width": root_geom.width,
            "height": root_geom.height,
        }

    def _randr_get_version(self) -> tuple[int, int] | None:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        randr_ext_data = xcb.get_extension_data(self.conn, LIB.randr_id)
        if not randr_ext_data.present:
            return None

        randr_version_data = xcb.randr_query_version(self.conn, xcb.RANDR_MAJOR_VERSION, xcb.RANDR_MINOR_VERSION)
        return (randr_version_data.major_version, randr_version_data.minor_version)

    def _randr_get_primary_output(self, randr_version: tuple[int, int], /) -> xcb.RandrOutput | None:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        if randr_version >= (1, 3):
            primary_output_data = xcb.randr_get_output_primary(self.conn, self.drawable)
            return primary_output_data.output
        # Python None means that there was no way to identify a primary output.  This is distinct from XCB_NONE (that
        # is, xcb.RandROutput(0)), which means that there is not a primary monitor.
        return None

    def _randr_get_edid_atom(self) -> xcb.Atom | None:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        edid_atom = xcb.intern_atom(self.conn, "EDID", only_if_exists=True)
        if edid_atom is not None:
            return edid_atom

        # Formerly, "EDID" was known as "EdidData".  I don't know when it changed.
        return xcb.intern_atom(self.conn, "EdidData", only_if_exists=True)

    def _randr_output_ids(
        self,
        output: xcb.RandrOutput,
        timestamp: xcb.Timestamp,
        edid_atom: xcb.Atom | None,
        /,
    ) -> dict[str, Any]:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        output_info = xcb.randr_get_output_info(self.conn, output, timestamp)
        if output_info.status != 0:
            msg = "Display configuration changed while detecting monitors."
            raise ScreenShotError(msg)

        rv: dict[str, Any] = {}

        output_name_arr = xcb.randr_get_output_info_name(output_info)
        rv["output"] = bytes(output_name_arr).decode("utf_8", errors="replace")

        if edid_atom is not None:
            edid_prop = xcb.randr_get_output_property(
                self.conn,  # connection
                output,  # output
                edid_atom,  # property
                xcb.XCB_NONE,  # property type: Any
                0,  # long-offset: 0
                1024,  # long-length: in 4-byte units; 4k is plenty for an EDID
                0,  # delete: false
                0,  # pending: false
            )
            if edid_prop.type_.value != 0:
                edid_block = bytes(xcb.randr_get_output_property_data(edid_prop))
                edid_data = parse_edid(edid_block)
                if (display_name := edid_data.get("display_name")) is not None:
                    rv["name"] = display_name

                edid_params: dict[str, str] = {}
                if (id_legacy := edid_data.get("id_legacy")) is not None:
                    edid_params["model"] = id_legacy
                if (serial_number := edid_data.get("serial_number")) is not None:
                    edid_params["serial"] = str(serial_number)
                if (manufacture_year := edid_data.get("manufacture_year")) is not None:
                    if (manufacture_week := edid_data.get("manufacture_week")) is not None:
                        edid_params["mfr_date"] = f"{manufacture_year:04d}W{manufacture_week:02d}"
                    else:
                        edid_params["mfr_date"] = f"{manufacture_year:04d}"
                if (model_year := edid_data.get("model_year")) is not None:
                    edid_params["model_year"] = f"{model_year:04d}"
                if edid_params:
                    rv["unique_id"] = urlencode(edid_params)

        return rv

    @staticmethod
    def _choose_randr_output(
        outputs: Array[xcb.RandrOutput], primary_output: xcb.RandrOutput | None, /
    ) -> xcb.RandrOutput:
        if len(outputs) == 0:
            msg = "No RandR outputs available"
            raise ScreenShotError(msg)
        if primary_output is None:
            # We don't want to use the `in` check if this could be None, according to MyPy.
            return outputs[0]
        return primary_output if primary_output in outputs else outputs[0]

    def _monitors_from_randr_monitors(
        self, primary_output: xcb.RandrOutput | None, edid_atom: xcb.Atom | None, /
    ) -> Monitors:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        monitors = []

        monitors_reply = xcb.randr_get_monitors(self.conn, self.drawable, 1)
        timestamp = monitors_reply.timestamp
        for randr_monitor in xcb.randr_get_monitors_monitors(monitors_reply):
            monitor = {
                "left": randr_monitor.x,
                "top": randr_monitor.y,
                "width": randr_monitor.width,
                "height": randr_monitor.height,
                # Under XRandR, it's legal for no monitor to be primary.  In this case, case MSSBase.primary_monitor
                # will return the first monitor.  That said, we note in the dict that we explicitly are told by XRandR
                # that all of the monitors are not primary.  (This is distinct from the XRandR 1.2 path, which doesn't
                # have any information about primary monitors.)
                "is_primary": bool(randr_monitor.primary),
            }

            if randr_monitor.nOutput > 0:
                outputs = xcb.randr_monitor_info_outputs(randr_monitor)
                chosen_output = self._choose_randr_output(outputs, primary_output)
                monitor |= self._randr_output_ids(chosen_output, timestamp, edid_atom)

            monitors.append(monitor)

        return monitors

    def _monitors_from_randr_crtcs(
        self,
        randr_version: tuple[int, int],
        primary_output: xcb.RandrOutput | None,
        edid_atom: xcb.Atom | None,
        /,
    ) -> Monitors:
        if self.conn is None:
            msg = "Cannot identify monitors while the connection is closed"
            raise ScreenShotError(msg)

        monitors = []

        screen_resources: xcb.RandrGetScreenResourcesReply | xcb.RandrGetScreenResourcesCurrentReply
        if hasattr(LIB.randr, "xcb_randr_get_screen_resources_current") and randr_version >= (1, 3):
            screen_resources = xcb.randr_get_screen_resources_current(self.conn, self.drawable)
            crtcs = xcb.randr_get_screen_resources_current_crtcs(screen_resources)
        else:
            screen_resources = xcb.randr_get_screen_resources(self.conn, self.drawable)
            crtcs = xcb.randr_get_screen_resources_crtcs(screen_resources)
        timestamp = screen_resources.config_timestamp

        for crtc in crtcs:
            crtc_info = xcb.randr_get_crtc_info(self.conn, crtc, timestamp)
            if crtc_info.num_outputs == 0:
                continue
            monitor = {
                "left": crtc_info.x,
                "top": crtc_info.y,
                "width": crtc_info.width,
                "height": crtc_info.height,
            }

            outputs = xcb.randr_get_crtc_info_outputs(crtc_info)
            chosen_output = self._choose_randr_output(outputs, primary_output)
            monitor |= self._randr_output_ids(chosen_output, timestamp, edid_atom)
            # The concept of primary outputs was added in XRandR 1.3.  We distinguish between "all the monitors are
            # not primary" (RRGetOutputPrimary returned XCB_NONE, a valid case) and "we have no way to get
            # information about the primary monitor": in the latter case, we don't populate "is_primary".
            if primary_output is not None:
                monitor["is_primary"] = chosen_output == primary_output

            monitors.append(monitor)

        return monitors

    def _cursor_check_xfixes(self) -> bool:
        """Check XFixes availability and version.

        :returns: ``True`` if the server provides XFixes with a compatible
            version, otherwise ``False``.
        """
        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)

        xfixes_ext_data = xcb.get_extension_data(self.conn, LIB.xfixes_id)
        if not xfixes_ext_data.present:
            return False

        reply = xcb.xfixes_query_version(self.conn, xcb.XFIXES_MAJOR_VERSION, xcb.XFIXES_MINOR_VERSION)
        # We can work with 2.0 and later, but not sure about the actual minimum version we can use.  That's ok;
        # everything these days is much more modern.
        return (reply.major_version, reply.minor_version) >= (2, 0)

    def cursor(self) -> ScreenShot:
        """Capture the current cursor image.

        Pixels are returned in BGRA ordering.

        :returns: A screenshot object containing the cursor image and region.
        """

        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)

        if self._xfixes_ready is None:
            self._xfixes_ready = self._cursor_check_xfixes()
        if not self._xfixes_ready:
            msg = "Server does not have XFixes, or the version is too old."
            raise ScreenShotError(msg)

        cursor_img = xcb.xfixes_get_cursor_image(self.conn)
        region = {
            "left": cursor_img.x - cursor_img.xhot,
            "top": cursor_img.y - cursor_img.yhot,
            "width": cursor_img.width,
            "height": cursor_img.height,
        }

        data_arr = xcb.xfixes_get_cursor_image_cursor_image(cursor_img)
        data = bytearray(data_arr)
        # We don't need to do the same array slice-and-dice work as the Xlib-based implementation: Xlib has an
        # unfortunate historical accident that makes it have to return the cursor image in a different format.

        return ScreenShot(data, region)

    def _grab_xgetimage(self, monitor: Monitor, /) -> bytearray:
        """Retrieve pixels from a monitor using ``GetImage``.

        Used by the XGetImage backend and by the XShmGetImage backend in
        fallback mode.

        :param monitor: Monitor rectangle specifying ``left``, ``top``,
            ``width``, and ``height`` to capture.
        :returns: A screenshot object containing the captured region.
        """

        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)

        img_reply = xcb.get_image(
            self.conn,
            xcb.ImageFormat.ZPixmap,
            self.drawable,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            ALL_PLANES,
        )

        # Now, save the image.  This is a reference into the img_reply structure.
        img_data_arr = xcb.get_image_data(img_reply)
        # Copy this into a new bytearray, so that it will persist after we clear the image structure.
        img_data = bytearray(img_data_arr)

        if img_reply.depth != self.drawable_depth or img_reply.visual != self.drawable_visual_id:
            # This should never happen; a window can't change its visual.
            msg = (
                "Server returned an image with a depth or visual different than it initially reported: "
                f"expected {self.drawable_depth},{hex(self.drawable_visual_id.value)}, "
                f"got {img_reply.depth},{hex(img_reply.visual.value)}"
            )
            raise ScreenShotError(msg)

        return img_data
