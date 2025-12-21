"""XCB backend using MIT-SHM XShmGetImage with automatic fallback.

This implementation prefers shared-memory captures for performance and will
fall back to XGetImage when the MIT-SHM extension is unavailable or fails at
runtime. The fallback reason is exposed via ``shm_fallback_reason`` to aid
debugging.
"""

from __future__ import annotations

import enum
import os
from mmap import PROT_READ, mmap  # type: ignore[attr-defined]
from typing import TYPE_CHECKING, Any

from mss.exception import ScreenShotError
from mss.linux import xcb
from mss.linux.xcbhelpers import LIB, XProtoError

from .base import ALL_PLANES, MSSXCBBase

if TYPE_CHECKING:
    from mss.models import Monitor
    from mss.screenshot import ScreenShot


class ShmStatus(enum.Enum):
    """Availability of the MIT-SHM extension for this backend."""

    UNKNOWN = enum.auto()  # Constructor says SHM *should* work, but we haven't seen a real GetImage succeed yet.
    AVAILABLE = enum.auto()  # We've successfully used XShmGetImage at least once.
    UNAVAILABLE = enum.auto()  # We know SHM GetImage is unusable; always use XGetImage.


class MSS(MSSXCBBase):
    """XCB backend using XShmGetImage with an automatic XGetImage fallback.

    The ``shm_status`` attribute tracks whether shared memory is available,
    and ``shm_fallback_reason`` records why a fallback occurred when MIT-SHM
    cannot be used.
    """

    def __init__(self, /, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # These are the objects we need to clean up when we shut down.  They are created in _setup_shm.
        self._memfd: int | None = None
        self._buf: mmap | None = None
        self._shmseg: xcb.ShmSeg | None = None

        # Rather than trying to track the shm_status, we may be able to raise an exception in __init__ if XShmGetImage
        # isn't available.  The factory in linux/__init__.py could then catch that and switch to XGetImage.
        # The conditions under which the attach will succeed but the xcb_shm_get_image will fail are extremely
        # rare, and I haven't yet found any that also will work with xcb_get_image.
        self.shm_status: ShmStatus = self._setup_shm()
        self.shm_fallback_reason: str | None = None

    def _shm_report_issue(self, msg: str, *args: Any) -> None:
        """Debugging hook for troubleshooting MIT-SHM issues.

        This will be called whenever MIT-SHM is disabled.  The optional
        arguments are not well-defined; exceptions are common.
        """
        full_msg = msg
        if args:
            full_msg += " | " + ", ".join(str(arg) for arg in args)
        self.shm_fallback_reason = full_msg

    def _setup_shm(self) -> ShmStatus:  # noqa: PLR0911
        assert self.conn is not None  # noqa: S101

        try:
            shm_ext_data = xcb.get_extension_data(self.conn, LIB.shm_id)
            if not shm_ext_data.present:
                self._shm_report_issue("MIT-SHM extension not present")
                return ShmStatus.UNAVAILABLE

            # We use the FD-based version of ShmGetImage, so we require the extension to be at least 1.2.
            shm_version_data = xcb.shm_query_version(self.conn)
            shm_version = (shm_version_data.major_version, shm_version_data.minor_version)
            if shm_version < (1, 2):
                self._shm_report_issue("MIT-SHM version too old", shm_version)
                return ShmStatus.UNAVAILABLE

            # We allocate something large enough for the root, so we don't have to reallocate each time the window is
            # resized.
            self._bufsize = self.pref_screen.width_in_pixels * self.pref_screen.height_in_pixels * 4

            if not hasattr(os, "memfd_create"):
                self._shm_report_issue("os.memfd_create not available")
                return ShmStatus.UNAVAILABLE
            try:
                self._memfd = os.memfd_create("mss-shm-buf", flags=os.MFD_CLOEXEC)  # type: ignore[attr-defined]
            except OSError as e:
                self._shm_report_issue("memfd_create failed", e)
                self._shutdown_shm()
                return ShmStatus.UNAVAILABLE
            os.ftruncate(self._memfd, self._bufsize)

            try:
                self._buf = mmap(self._memfd, self._bufsize, prot=PROT_READ)  # type: ignore[call-arg]
            except OSError as e:
                self._shm_report_issue("mmap failed", e)
                self._shutdown_shm()
                return ShmStatus.UNAVAILABLE

            self._shmseg = xcb.ShmSeg(xcb.generate_id(self.conn).value)
            try:
                # This will normally be what raises an exception if you're on a remote connection.
                # XCB will close _memfd, on success or on failure.
                try:
                    xcb.shm_attach_fd(self.conn, self._shmseg, self._memfd, read_only=False)
                finally:
                    self._memfd = None
            except xcb.XError as e:
                self._shm_report_issue("Cannot attach MIT-SHM segment", e)
                self._shutdown_shm()
                return ShmStatus.UNAVAILABLE

        except Exception:
            self._shutdown_shm()
            raise

        return ShmStatus.UNKNOWN

    def _close_impl(self) -> None:
        self._shutdown_shm()
        super()._close_impl()

    def _shutdown_shm(self) -> None:
        # It would be nice to also try to tell the server to detach the shmseg, but we might be in an error path
        # and don't know if that's possible.  It's not like we'll leak a lot of them on the same connection anyway.
        # This can be called in the path of partial initialization.
        if self._buf is not None:
            self._buf.close()
            self._buf = None
        if self._memfd is not None:
            os.close(self._memfd)
            self._memfd = None

    def _grab_impl_xshmgetimage(self, monitor: Monitor) -> ScreenShot:
        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)
        assert self._buf is not None  # noqa: S101
        assert self._shmseg is not None  # noqa: S101

        required_size = monitor["width"] * monitor["height"] * 4
        if required_size > self._bufsize:
            # This is temporary.  The permanent fix will depend on how
            # issue https://github.com/BoboTiG/python-mss/issues/432 is resolved.
            msg = (
                "Requested capture size exceeds the allocated buffer. If you have resized the screen, "
                "please recreate your MSS object."
            )
            raise ScreenShotError(msg)

        img_reply = xcb.shm_get_image(
            self.conn,
            self.drawable.value,
            monitor["left"],
            monitor["top"],
            monitor["width"],
            monitor["height"],
            ALL_PLANES,
            xcb.ImageFormat.ZPixmap,
            self._shmseg,
            0,
        )

        if img_reply.depth != self.drawable_depth or img_reply.visual.value != self.drawable_visual_id:
            # This should never happen; a window can't change its visual.
            msg = (
                "Server returned an image with a depth or visual different than it initially reported: "
                f"expected {self.drawable_depth},{hex(self.drawable_visual_id)}, "
                f"got {img_reply.depth},{hex(img_reply.visual.value)}"
            )
            raise ScreenShotError(msg)

        # Snapshot the buffer into new bytearray.
        new_size = monitor["width"] * monitor["height"] * 4
        # Slicing the memoryview creates a new memoryview that points to the relevant subregion.  Making this and
        # then copying it into a fresh bytearray is much faster than slicing the mmap object.
        img_mv = memoryview(self._buf)[:new_size]
        img_data = bytearray(img_mv)

        return self.cls_image(img_data, monitor)

    def _grab_impl(self, monitor: Monitor) -> ScreenShot:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        if self.shm_status == ShmStatus.UNAVAILABLE:
            return super()._grab_impl_xgetimage(monitor)

        # The usual path is just the next few lines.
        try:
            rv = self._grab_impl_xshmgetimage(monitor)
            self.shm_status = ShmStatus.AVAILABLE
        except XProtoError as e:
            if self.shm_status != ShmStatus.UNKNOWN:
                # We know XShmGetImage works, because it worked earlier.  Reraise the error.
                raise

            # Should we engage the fallback path?  In almost all cases, if XShmGetImage failed at this stage (after
            # all our testing in __init__), XGetImage will also fail.  This could mean that the user sent an
            # out-of-bounds request.  In more exotic situations, some rare X servers disallow screen capture
            # altogether: security-hardened servers, for instance, or some XPrint servers.  But let's make sure, by
            # testing the same request through XGetImage.
            try:
                rv = super()._grab_impl_xgetimage(monitor)
            except XProtoError:  # noqa: TRY203
                # The XGetImage also failed, so we don't know anything about whether XShmGetImage is usable.  Maybe
                # the user sent an out-of-bounds request.  Maybe it's a security-hardened server.  We're not sure what
                # the problem is.  So, if XGetImage failed, we re-raise that error (the one from XShmGetImage will be
                # attached as __context__), but we won't update the shm_status yet.  (Technically, our except:raise
                # clause here is redundant; it's just for clarity, to hold this comment.)
                raise

            # Using XShmGetImage failed, and using XGetImage worked.  Use XGetImage in the future.
            self._shm_report_issue("MIT-SHM GetImage failed", e)
            self.shm_status = ShmStatus.UNAVAILABLE
            self._shutdown_shm()

        return rv
