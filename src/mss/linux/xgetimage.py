"""XCB-based backend using the XGetImage request.

This backend issues XCB ``GetImage`` requests and supports the RandR and
XFixes extensions when available for monitor enumeration and cursor capture.

This backend will work on any X connection, but is slower than the xshmgetimage
backend.

.. versionadded:: 10.2.0
"""

from mss.models import Monitor
from mss.screenshot import ScreenShot

from .base import MSSXCBBase


class MSS(MSSXCBBase):
    """XCB backend using XGetImage requests on GNU/Linux."""

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        return super()._grab_impl_xgetimage(monitor)
