from __future__ import annotations

import errno
import os
from mmap import PROT_READ, mmap  # type: ignore[attr-defined]
from typing import TYPE_CHECKING, Any, Literal

from mss.exception import ScreenShotError
from mss.linux import xcb
from mss.linux.xcbhelpers import LIB, XProtoError

from .base import ALL_PLANES, MSSXCBBase

if TYPE_CHECKING:
    from mss.models import Monitor
    from mss.screenshot import ScreenShot


class MSS(MSSXCBBase):
    """Multiple ScreenShots implementation for GNU/Linux.

    This implementation is based on XCB, using the ShmGetImage request.
    If ShmGetImage fails, then this will fall back to using GetImage.
    """

    def __init__(self, /, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # These are the objects we need to clean up when we shut down.  They are created in _setup_shm.
        self._memfd: int | None = None
        self._buf: mmap | None = None
        self._shmseg: xcb.ShmSeg | None = None

        # _shm_works is True if at least one screenshot has been taken, False if it's known to fail, and None until
        # then.
        self._shm_works: bool | None = self._setup_shm()

    def _shm_report_issue(self, msg: str, *args: Any) -> None:
        """Debugging hook for troubleshooting MIT-SHM issues.

        This will be called whenever MIT-SHM is disabled.  The optional
        arguments are not well-defined; exceptions are common.
        """
        print(msg, args)

    def _setup_shm(self) -> Literal[False] | None:
        assert self.conn is not None  # noqa: S101

        shm_ext_data = xcb.get_extension_data(self.conn, LIB.shm_id)
        if not shm_ext_data.present:
            self._shm_report_issue("MIT-SHM extension not present")
            return False

        # We use the FD-based version of ShmGetImage, so we require the extension to be at least 1.3.
        shm_version_data = xcb.shm_query_version(self.conn)
        shm_version = (shm_version_data.major_version, shm_version_data.minor_version)
        if shm_version < (1, 2):
            self._shm_report_issue("MIT-SHM version too old", shm_version)
            return False

        # We allocate something large enough for the root, so we don't have to reallocate each time the window is
        # resized.
        # TODO(jholveck): Check in _grab_impl that we're not going to exceed this size.  That can happen if the
        # root is resized.
        size = self.pref_screen.width_in_pixels * self.pref_screen.height_in_pixels * 4

        try:
            self._memfd = os.memfd_create("mss-shm-buf", flags=os.MFD_CLOEXEC)  # type: ignore[attr-defined]
        except OSError as e:
            self._shm_report_issue("memfd_create failed", e)
            self._shutdown_shm()
            return False
        os.ftruncate(self._memfd, size)

        try:
            self._buf = mmap(self._memfd, size, prot=PROT_READ)  # type: ignore[call-arg]
        except OSError as e:
            self._shm_report_issue("mmap failed", e)
            self._shutdown_shm()
            return False

        self._shmseg = xcb.ShmSeg(xcb.generate_id(self.conn).value)
        try:
            # This will normally be what raises an exception if you're on a remote connection.  I previously thought
            # the server deferred that until the GetImage call, but I had not been properly checking the status here.
            xcb.shm_attach_fd(self.conn, self._shmseg, self._memfd, read_only=False)
        except xcb.XError as e:
            self._shm_report_issue("Cannot attach MIT-SHM segment", e)
            self._shutdown_shm()
            return False

        return None

    def close(self) -> None:
        self._shutdown_shm()
        super().close()

    def _shutdown_shm(self) -> None:
        # It would be nice to also try to tell the server to detach the shmseg, but we might be in an error path
        # and don't know if that's possible.  It's not like we'll leak a lot of them on the same connection anyway.
        # This can be called in the path of partial initialization.
        if self._buf is not None:
            self._buf.close()
            self._buf = None
        if self._memfd is not None:
            # TODO(jholveck): For some reason, at this point, self._memfd is no longer valid.  If I try to close it,
            # I get EBADF, even if I try to close it before closing the mmap.  The theories I have about this involve
            # the mmap object taking control, but it doesn't make sense that I could still use shm_attach_fd in that
            # case.  I need to investigate before releasing.
            try:
                os.close(self._memfd)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            self._memfd = None

    def _grab_impl_xshmgetimage(self, monitor: Monitor) -> ScreenShot:
        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)
        assert self._buf is not None  # noqa: S101
        assert self._shmseg is not None  # noqa: S101

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
        if self._shm_works == False:  # noqa: E712
            return super()._grab_impl_xgetimage(monitor)

        try:
            rv = self._grab_impl_xshmgetimage(monitor)
        except XProtoError as e:
            if self._shm_works is not None:
                raise
            self._shm_report_issue("MIT-SHM GetImage failed", e)
            self._shm_works = False
            self._shutdown_shm()
            rv = super()._grab_impl_xgetimage(monitor)
        else:
            self._shm_works = True

        return rv
