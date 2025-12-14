"""XCB-based backend using the XGetImage request.

This backend issues XCB ``GetImage`` requests and supports the RandR and
XFixes extensions when available for monitor enumeration and cursor capture.
"""

from mss.models import Monitor
from mss.screenshot import ScreenShot

from .base import MSSXCBBase


class MSS(MSSXCBBase):
    """XCB backend using XGetImage requests on GNU/Linux.

    Uses RandR (for monitor enumeration) and XFixes (for cursor capture) when
    available.
    """

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        return super()._grab_impl_xgetimage(monitor)
