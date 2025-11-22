from mss.exception import ScreenShotError
from mss.models import Monitor
from mss.screenshot import ScreenShot

from . import xcb
from .base import ALL_PLANES, MSSXCBBase


class MSS(MSSXCBBase):
    """Multiple ScreenShots implementation for GNU/Linux.

    This implementation is based on XCB, using the GetImage request.
    It can optionally use some extensions:
    * RandR: Enumerate individual monitors' sizes.
    * XFixes: Including the cursor.
    """

    def _grab_impl(self, monitor: Monitor, /) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""

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

        if img_reply.depth != self.drawable_depth or img_reply.visual.value != self.drawable_visual_id:
            # This should never happen; a window can't change its visual.
            msg = (
                "Server returned an image with a depth or visual different than it initially reported: "
                f"expected {self.drawable_depth},{hex(self.drawable_visual_id)}, "
                f"got {img_reply.depth},{hex(img_reply.visual.value)}"
            )
            raise ScreenShotError(msg)

        return self.cls_image(img_data, monitor)
