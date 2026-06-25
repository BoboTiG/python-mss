"""Buffers with Finalizers

This is an implementation of buffer objects with Python finalizers,
specific to the needs of MSS.

# Caller Contract

The entry point is `finalizing_buffer`.  This is intended to be called
by `MSSImplementation` subclasses.  They provide a buffer (such as a
ctypes array or mmap object) and a finalizer, and are given a
`memoryview` object.  Once the memoryview is garbage collected, and
the consumers downstream of that memoryview have released their views
of the buffer, the finalizer will be invoked (with no arguments).

At that time, the `MSSImplementation` may release the buffer, return
it to a pool for reuse, etc.

This finalizer may be called at any time, from any thread.  It may be
called after the MSSImplementation's `close()` method has been called.
Implementations must take care not to invalidate their buffers during
`close()`, but rather only after finalization.

The finalizer may also be called before `finalizing_buffer()` returns.
This may happen if the implementation needs to make a copy rather than
using the originally-provided buffer (which is the case on Python
versions prior to 3.12).

(Some more caveats appear at the end of this docstring.)

# Background

The Python buffer protocol lets different objects share underlying
memory.  For instance, a NumPy ndarray, a Python bytearray object, and
a PyTorch Tensor object can all share the same underlying memory.
This allows interoperability between these systems without requiring
copies.

Copying ("blitting") all the pixels in a screenshot takes time;
copying a 4K (3840x2160) BGRA image can take several milliseconds.  If
an application is attempting to operate at 60 FPS, each copy consumes
a meaningful fraction of the frame budget.

For a high-performance screenshot library such as MSS, it is therefore
important to minimize copies.  Ideally, screenshot data would remain
in the buffer originally allocated by the operating system, such as
the memory returned by CreateDIBSection on Windows or a shared memory
segment on X11.  This approach is commonly called "zero-copy".

Getting the buffer to the user is only half the problem.  MSS also
needs to know when the user is finished with the buffer's contents so
that the underlying resources can be reused or released.

Most code that uses the buffer protocol is written in C.  Since Python
3.0, the C-level buffer protocol has provided a mechanism for
exporters to learn when their buffers are no longer in use.  However,
the corresponding Python-level API (which can be used by C consumers)
was not added until Python 3.12.

Buffer lifetime is not the same as Python object lifetime.  A user may
pass the returned memoryview to NumPy, PIL, PyTorch, or other
libraries.  Those libraries may keep the exported buffer alive after
the original Python memoryview object is no longer reachable.

Therefore, the lifetime of the returned memoryview object is not a
reliable signal that the buffer is no longer in use.  Other objects
may still hold references to the buffer after that memoryview has been
destroyed.  To know when the buffer can safely be reused or released,
MSS relies on the buffer protocol's release mechanism.

The buffer protocol permits a wide variety of consumer behaviors and
derived-buffer relationships.  Rather than attempting to model all of
those interactions directly, this implementation delegates that
complexity to Python's existing buffer-management machinery.

## Performance note

As a rough reference, copying a 3840x2160 BGRA screenshot on
contemporary hardware (Amazon EC2 m8i.large, Intel Xeon 6, DDR5-7200)
takes approximately 2.5 ms. At 60 FPS, that is about 15% of the
available frame time for a single copy.  These numbers are intended
only to provide intuition about the cost of copies; actual performance
varies substantially by hardware and memory subsystem.

# Design

The central design decision in this file is that MSS interacts with
exactly one downstream buffer consumer: a memoryview.

A memoryview is Python's standard object for representing a buffer.
It already implements the reference tracking, buffer export, slicing,
and format-conversion behavior required by the buffer protocol.

Notably, memoryview objects do not pass buffer requests upstream to
arbitrary exporters.  Once a memoryview has been created, it manages
downstream consumers itself.

This means MSS only needs to reason about a single interaction: the
interaction between `_FinalizingBufferIntermediate` and the memoryview
created from it.

One idea that has been proposed is to attach a weakref finalizer
directly to a memoryview object and use that as the signal that the
buffer is no longer in use.  Testing has shown that this is not
sufficient.  A memoryview Python object may be finalized while
downstream consumers still hold active references to the underlying
buffer.

To obtain a correct signal, MSS uses the Python-side buffer protocol
introduced in Python 3.12 via the `__buffer__` and
`__release_buffer__` methods.

An instance of `_FinalizingBufferIntermediate` is created and exactly
one memoryview is constructed from it.  That memoryview is returned to
the caller.

The memoryview tracks all downstream users of the buffer.  When all of
those users have released their references, the memoryview
automatically invokes `_FinalizingBufferIntermediate.__release_buffer__`.

That method invokes the caller-provided finalizer, which can release
or recycle the underlying storage.

If this implementation appears more indirect than necessary, that
indirection is intentional.  It narrows the portion of the buffer
protocol that MSS must reason about and test.

# Caveats and Invariants

* The finalizer may run after `MSSImplementation.close()` has been
  called.  `close()` must not free, reuse, or otherwise invalidate
  buffers that may still be visible to users.

* The finalizer may run at any time and on any thread.  Finalizer code
  must therefore be thread-safe and must not assume that it executes
  on the thread that created the buffer.

* On Python versions prior to 3.12, `finalizing_buffer()` creates a
  copy of the data and invokes the finalizer immediately.  In this
  case, the finalizer may run before `finalizing_buffer()` returns.

* `_FinalizingBufferIntermediate` intentionally supports exactly one
  buffer request.  This restriction simplifies reasoning about
  correctness and should not be removed without carefully considering
  the resulting buffer-lifetime semantics.

* `_FinalizingBufferIntermediate` remains reachable through
  `memoryview.obj`.  Consumers must treat this as an implementation
  detail and must not invoke `__buffer__()` or `__release_buffer__()`
  directly.

* Finalizer execution during interpreter shutdown is not guaranteed.
  Implementations should not rely on finalizers running during process
  termination.
"""

from __future__ import annotations

import sys
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import Buffer

# You can always use this module, and finalizing_buffer.  This variable is for conditionalizing things like test code or
# optimizations, but most code should always follow the same path.
FAST_PATH_AVAILABLE = sys.version_info >= (3, 12)


class _FinalizingBufferIntermediate:
    """Finalizing buffer class.

    Contrary to the buffer protocol, this class only allows a single
    buffer to be created.  This simplifies the implementation and
    reasoning.

    The creator must provide a finalizer to ensure that resources are
    properly released when the underlying buffer is no longer needed.
    This will be invoked, with no arguments, after all the downstream
    users, such as NumPy or PIL, have released their references to
    the buffer.

    This is only useful on Python 3.12 and later; earlier versions do
    not support the __buffer__ and __release_buffer__ methods.

    This class should only be used by the finalizing_buffer function.
    It is not appropriate for other uses!
    """

    def __init__(self, data: Buffer, finalizer: Callable) -> None:
        self._mv: memoryview | None = memoryview(data)
        self._finalizer = finalizer
        # The remainder of these shouldn't be necessary.  As a consequence of the __buffer__ contract and the
        # implementation of finalizing_buffer, only one call to __buffer__ and one call to __release_buffer__ should be
        # made, and never simultaneously.  But we still include them out of an abundance of caution.
        self._buffer_invoked = False
        self._release_invoked = False
        self._lock = Lock()

    def __buffer__(self, _flags: int) -> memoryview:
        with self._lock:
            assert not self._buffer_invoked, "Buffer can only be requested once"  # noqa: S101
            self._buffer_invoked = True
        assert self._mv is not None, "Buffer has already been released"  # noqa: S101
        return self._mv

    def __release_buffer__(self, _buffer: memoryview) -> None:
        with self._lock:
            assert not self._release_invoked, "Buffer can only be released once"  # noqa: S101
            self._release_invoked = True
        assert self._mv is not None, "Buffer has already been released"  # noqa: S101
        # We need to release the memoryview itself, so that when the finalizer is invoked, the underlying buffer object
        # doesn't think there are still exported buffers.  (mmap, for instance, won't close a region with exported
        # buffers.)
        self._mv.release()
        self._mv = None  # Extra-defensive
        self._finalizer()


def finalizing_buffer(data: Buffer, finalizer: Callable) -> memoryview:
    """Create a finalizing buffer or a copy depending on Python version.

    The finalizer will be invoked when the buffer is no longer in use,
    with a caveat.  This will only track uses downstream of the
    returned buffer.  If the input buffer is also used in other
    places, those are not accounted for.

    On Python 3.12 and later, this returns a memoryview object that
    provides a reusable buffer interface.  On earlier versions, this
    returns a copy of the data, and invokes the finalizer immediately
    after the copy is made.

    This preserves read/write semantics of the original data: if the
    original buffer is read-only, the returned memoryview will be
    read-only.
    """
    if FAST_PATH_AVAILABLE:
        # Fast path: we can use the Python 3.12 features
        return memoryview(_FinalizingBufferIntermediate(data, finalizer))
    # Slow path: copy the data.
    with memoryview(data) as mv:
        # We create a memoryview of the original data so that we can tell if it's read-only or not.  We can't return
        # this memoryview, since we're about to invoke the finalizer to release the buffer it got its data from.
        copied_data = bytes(mv) if mv.readonly else bytearray(mv)
    finalizer()
    # We could return copied_data directly and still have a perfectly fine buffer, but always returning a memoryview
    # provides more consistency.
    return memoryview(copied_data)
