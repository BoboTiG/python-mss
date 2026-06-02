"""XCB-based backend using the XGetImage request.

This backend issues XCB ``GetImage`` requests and supports the RandR and
XFixes extensions when available for monitor enumeration and cursor capture.

This backend will work on any X connection, but is slower than the xshmgetimage
backend.

.. versionadded:: 10.2.0
"""

from mss.linux.base import MSSImplXCBBase
from mss.models import Monitor

__all__ = ()


class MSSImplXGetImage(MSSImplXCBBase):
    """XCB backend using XGetImage requests on GNU/Linux.

    .. seealso::
        :py:class:`mss.linux.base.MSSXCBBase`
            Lists constructor parameters.
    """

    def grab(self, monitor: Monitor) -> bytearray:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        return super()._grab_xgetimage(monitor)
