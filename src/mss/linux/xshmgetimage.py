"""XCB backend using MIT-SHM XShmGetImage with automatic fallback.

This is the fastest Linux backend available, and will work in most common
cases. However, it will not work over remote X connections, such as over ssh.

This implementation prefers shared-memory captures for performance and will
fall back to XGetImage when the MIT-SHM extension is unavailable or fails at
runtime. The fallback reason is exposed via ``performance_status`` to aid
debugging.

.. versionadded:: 10.2.0
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass
from functools import partial
from mmap import PROT_READ, PROT_WRITE, mmap  # type: ignore[attr-defined]
from threading import RLock
from typing import TYPE_CHECKING, Any

from mss.buffer import FAST_PATH_AVAILABLE, finalizing_buffer
from mss.exception import ScreenShotError
from mss.linux import xcb
from mss.linux.base import ALL_PLANES, MSSImplXCBBase
from mss.linux.xcbhelpers import LIB, XProtoError

if TYPE_CHECKING:
    from mss.models import Monitor

__all__ = ()

# For Python < 3.12, we only use one buffer.
#
# For Python >= 3.12, we have zero-copy buffers that the user owns.  For those, we allocate two initial buffers.  This
# is for the common case:
#
#   with mss() as sct:
#       while True:
#         img = sct.grab(...)  # noqa: ERA001
#         process(img)         # noqa: ERA001
#
# In that case, each ScreenShot object is not released until the next one has been assigned to img.  That means that we
# will need two buffers to handle that case zero-copy.  Our free pool can always grow, but we start it with two to keep
# the second capture from having a brief hiccup.
_INITIAL_BUFFER_COUNT = 2 if FAST_PATH_AVAILABLE else 1


class ShmStatus(enum.Enum):
    """Availability of the MIT-SHM extension for this backend."""

    UNKNOWN = enum.auto()  # Constructor says SHM *should* work, but we haven't seen a real GetImage succeed yet.
    AVAILABLE = enum.auto()  # We've successfully used XShmGetImage at least once.
    UNAVAILABLE = enum.auto()  # We know SHM GetImage is unusable; always use XGetImage.


@dataclass(slots=True)
class _ShmSlot:
    shmseg: xcb.ShmSeg
    buf: mmap | None  # Set to None when it's closed, for extra verification
    size: int


class MSSImplXShmGetImage(MSSImplXCBBase):
    """XCB backend using XShmGetImage with an automatic XGetImage fallback.

    .. seealso::
        :py:class:`mss.linux.base.MSSImplXCBBase`
            Lists constructor parameters.
    """

    def __init__(self, *, display: str | bytes | None = None, with_cursor: bool = False) -> None:
        super().__init__(display=display, with_cursor=with_cursor)

        # Protects SHM pool state and serializes XCB detach/disconnect calls.
        # RLock is intentional: finalizers may run in re-entrant contexts.
        self._shm_lock = RLock()
        # Free-list ownership model:
        # - a slot in this list is idle and available for reuse;
        # - a slot removed from this list is owned by grab/finalizer flow;
        # - finalization returns it here unless SHM has been closed (in which case it is destroyed)
        # Protected by _shm_lock.
        self._free_shm_slots: list[_ShmSlot] = []
        # Once this is set, we no longer expect to use SHM and have
        # released the idle standby buffers already.
        # Protected by _shm_lock.
        self._shm_closed = False
        # Once set, SHM slot destruction should not attempt XCB shm_detach.  This is because we're about to close the
        # XCB connection (possibly in a different thread), and so XCB calls may fail.  We'll just let the X server clean
        # up the segments when the connection closes.
        # Protected by _shm_lock.
        self._closing_conn = False

        # Rather than trying to track the shm_status, we may be able to raise an exception in __init__ if XShmGetImage
        # isn't available.  The factory in linux/__init__.py could then catch that and switch to XGetImage.
        # The conditions under which the attach will succeed but the xcb_shm_get_image will fail are extremely
        # rare, and I haven't yet found any that also will work with xcb_get_image.
        #: Whether we can use the MIT-SHM extensions for this connection.
        #: This will not be ``AVAILABLE`` until at least one capture has succeeded.
        #: It may be set to ``UNAVAILABLE`` sooner.
        self.shm_status: ShmStatus = self._setup_shm()

    def _shm_report_issue(self, msg: str, *args: Any) -> None:
        """Debugging hook for troubleshooting MIT-SHM issues.

        This will be called whenever MIT-SHM is disabled.  The optional
        arguments are not well-defined; exceptions are common.
        """
        full_msg = msg
        if args:
            full_msg += " | " + ", ".join(str(arg) for arg in args)
        self.performance_status.append(full_msg)

    def _create_shm_slot(self, size: int) -> _ShmSlot:
        """Allocate and attach one shared-memory slot.

        This is called when the free list is empty when a grab is
        requested.  The caller owns the new slot, and is responsible for
        ensuring it is put on the free list or destroyed.
        """
        assert self.conn is not None  # noqa: S101

        memfd: int | None = None
        mm: mmap | None = None
        try:
            try:
                memfd = os.memfd_create("mss-shm-buf", flags=os.MFD_CLOEXEC)  # type: ignore[attr-defined]
            except OSError as exc:
                msg = "Cannot allocate MIT-SHM buffer"
                raise ScreenShotError(msg) from exc

            try:
                os.ftruncate(memfd, size)
            except OSError as exc:
                msg = "Cannot size MIT-SHM buffer"
                raise ScreenShotError(msg) from exc

            try:
                mm = mmap(memfd, size, prot=PROT_READ | PROT_WRITE)  # type: ignore[call-arg]
            except OSError as exc:
                msg = "Cannot map MIT-SHM buffer"
                raise ScreenShotError(msg) from exc

            shmseg = xcb.ShmSeg(xcb.generate_id(self.conn).value)

            # XCB closes memfd after this call, on success or failure.
            fd_for_attach = memfd
            memfd = None
            try:
                xcb.shm_attach_fd(self.conn, shmseg, fd_for_attach, read_only=False)
            except xcb.XError as exc:
                msg = "Cannot attach MIT-SHM segment"
                raise ScreenShotError(msg) from exc

            return _ShmSlot(shmseg=shmseg, buf=mm, size=size)
        except Exception:
            if mm is not None:
                mm.close()
            if memfd is not None:
                os.close(memfd)
            raise

    def _destroy_shm_slot(self, slot: _ShmSlot) -> None:
        """Detach and close one shared-memory slot.

        This is only called when or after the SHM pool is cleaned up:
        * By _cleanup_shm_slots, on free slots, either during close or
          if SHM is found to be unavailable, or
        * By the finalizer, if the slot is released after the MSS object
          is closed

        If the connection is not being closed (so we're in the path to
        fallback to XGetImage), we also tell the server that we're done
        with the memory region.  Conversely, during connection close, we
        skip explicit detach and let the server clean up the SHM
        resources when the connection is closed.
        """
        if slot.buf is None:
            return
        with self._shm_lock:
            # If we're about to close the X connection, there's no need to explicitly tell the server about the
            # detaches.  What's more, the connection might be in an error state.  We'll let the server detach all the
            # segments at once when we disconnect.  However, if we're destroying our SHM slots because XShmGetImage was
            # for some reason found to be unsuitable after we created them, then we should be nice and let the server
            # clean up resources.
            if not self._closing_conn:
                assert self.conn is not None  # noqa: S101  For MyPy
                # One possibility might be to make this a best-effort shutdown, not a hard failure.  However, I
                # generally don't like suppressing errors if there's not a compelling reason.
                xcb.shm_detach(self.conn, slot.shmseg)
        slot.buf.close()
        slot.buf = None

    def _acquire_shm_slot(self, required_size: int) -> _ShmSlot:
        """Take a slot from the free-list, growing if needed."""
        with self._shm_lock:
            assert not self._shm_closed, "SHM pool has already been closed"  # noqa: S101

            for idx, slot in enumerate(self._free_shm_slots):
                if slot.buf is not None and slot.size >= required_size:
                    self._free_shm_slots.pop(idx)
                    return slot

        # Create a new slot outside the lock to keep the critical section short.
        slot = self._create_shm_slot(max(required_size, self._bufsize))
        # Since SHM can only be closed and _acquire can only be called during __init__, grab, or close, and those all
        # hold a lock, shm cannot have been closed while we were creating the slot.
        assert not self._shm_closed, "SHM pool closed unexpectedly"  # noqa: S101

        return slot

    def _release_shm_slot(self, slot: _ShmSlot) -> None:
        """Return a slot to the free-list, or destroy it.

        This is called by the finalizer.  It might be called during
        grab, if a copy is needed, or at any time later.
        """
        with self._shm_lock:
            if not self._shm_closed:
                self._free_shm_slots.append(slot)
                return
        # SHM is already closed.  Destroy the slot now.
        self._destroy_shm_slot(slot)

    def _cleanup_shm_slots(self) -> None:
        """Retire SHM use and free any idle slots immediately.

        This is called during MSS close, or if SHM is discovered to be
        unusable during setup or grab.
        """
        with self._shm_lock:
            self._shm_closed = True
            idle_slots, self._free_shm_slots = self._free_shm_slots, []

        for slot in idle_slots:
            self._destroy_shm_slot(slot)

    def _shm_unavailable(self, msg: str, exc: Exception) -> ShmStatus:
        """Record why SHM was disabled and clean up the pool."""
        self._shm_report_issue(msg, exc)
        self._cleanup_shm_slots()
        return ShmStatus.UNAVAILABLE

    def _setup_shm(self) -> ShmStatus:
        """Probe MIT-SHM and seed the initial buffer pool."""
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

            # We allocate something large enough for the root for our initial buffers, to accommodate any grab request.
            self._bufsize = self.pref_screen.width_in_pixels * self.pref_screen.height_in_pixels * 4

            if not hasattr(os, "memfd_create"):
                self._shm_report_issue("os.memfd_create not available")
                return ShmStatus.UNAVAILABLE

            # Initialize the number of buffers we expect to need.
            for _ in range(_INITIAL_BUFFER_COUNT):
                self._free_shm_slots.append(self._create_shm_slot(self._bufsize))
        except ScreenShotError as e:
            return self._shm_unavailable("MIT-SHM setup failed", e)
        except Exception:
            self._cleanup_shm_slots()
            raise

        return ShmStatus.UNKNOWN

    def _grab_xshmgetimage(self, monitor: Monitor) -> memoryview:
        """Capture a monitor directly into a shared-memory slot."""
        if self.conn is None:
            msg = "Cannot take screenshot while the connection is closed"
            raise ScreenShotError(msg)

        # Presently, we request a buffer at least as big as our capture area.  Another option would be to request a
        # buffer at the root size: this uses more memory, but makes it more likely that the buffers can be reused after
        # window resizes.  This only matters if the initial buffers are in use still, and we have to create a new one.
        required_size = monitor["width"] * monitor["height"] * 4
        slot = self._acquire_shm_slot(required_size)
        assert slot.buf is not None  # noqa: S101

        try:
            img_reply = xcb.shm_get_image(
                self.conn,
                self.drawable,
                monitor["left"],
                monitor["top"],
                monitor["width"],
                monitor["height"],
                ALL_PLANES,
                xcb.ImageFormat.ZPixmap,
                slot.shmseg,
                0,
            )

            if img_reply.depth != self.drawable_depth or img_reply.visual != self.drawable_visual_id:
                # This should never happen; a window can't change its visual.
                msg = (
                    "Server returned an image with a depth or visual different than it initially reported: "
                    f"expected {self.drawable_depth},{hex(self.drawable_visual_id.value)}, "
                    f"got {img_reply.depth},{hex(img_reply.visual.value)}"
                )
                raise ScreenShotError(msg)  # noqa: TRY301 Clearer this way than what TRY301 wants

            finalizer = partial(self._release_shm_slot, slot)
            return finalizing_buffer(memoryview(slot.buf)[:required_size], finalizer)

        except Exception:
            self._release_shm_slot(slot)
            raise

    def grab(self, monitor: Monitor) -> memoryview | bytearray:
        """Retrieve all pixels from a monitor. Pixels have to be RGBX."""
        if self.shm_status == ShmStatus.UNAVAILABLE:
            return super()._grab_xgetimage(monitor)

        # The usual path is just the next few lines.
        try:
            rv: memoryview | bytearray = self._grab_xshmgetimage(monitor)
            if self.shm_status != ShmStatus.AVAILABLE:
                self.shm_status = ShmStatus.AVAILABLE
                self.performance_status.append("MIT-SHM is working correctly.")
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
                rv = super()._grab_xgetimage(monitor)
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
            self._cleanup_shm_slots()

        return rv

    def close(self) -> None:
        """Release SHM resources and then close the XCB connection."""
        with self._shm_lock:
            self._closing_conn = True
        self._cleanup_shm_slots()
        with self._shm_lock:
            super().close()
