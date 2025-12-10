from mss.models import Monitor
from mss.screenshot import ScreenShot

from .base import MSSXCBBase


class MSS(MSSXCBBase):
    """Multiple ScreenShots implementation for GNU/Linux.

    This implementation is based on XCB, using the GetImage request.
    It can optionally use some extensions:
    * RandR: Enumerate individual monitors' sizes.
    * XFixes: Including the cursor.
    """

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        return super()._grab_impl_xgetimage(monitor)
