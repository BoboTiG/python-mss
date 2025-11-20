from __future__ import annotations

import ctypes.util
from contextlib import suppress
from copy import copy
from ctypes import (
    CDLL,
    POINTER,
    Array,
    Structure,
    _Pointer,
    addressof,
    c_char_p,
    c_int,
    c_uint,
    c_uint8,
    c_uint16,
    c_uint32,
    c_void_p,
    cast,
    cdll,
)
from threading import RLock
from typing import TYPE_CHECKING
from weakref import finalize

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import Any

from mss.exception import ScreenShotError

# A quick refresher on why this module spends so much effort on object lifetimes, and how the pieces fit together:
#
# 1. Shape of XCB replies.
#    Each reply that comes back from libxcb is one contiguous allocation that looks like:
#       [fixed-size header][optional padding][embedded arrays/lists]
#    The protocol spec describes where those trailing lists live, but callers are not expected to compute offsets by
#    hand.  Instead, XCB exposes helper functions such as `xcb_setup_pixmap_formats` (returns pointer + length for a
#    fixed-size array) or iterator factories for nested variable-length data.  As long as the original reply is still
#    allocated, all of the derived pointers remain valid.
#
# 2. What ctypes does (and does not) track automatically.
#    When user code reads `my_struct.foo`, ctypes returns another ctypes object that still refers to memory owned by
#    `my_struct`; it does not copy the value.  To keep that relationship alive, ctypes silently sets `_b_base_` on the
#    derived object so the garbage collector knows that `my_struct` must stay around.  This mechanism only works when
#    ctypes itself materializes the derived object.
#
# 3. Why XCB accessors break that safety net.
#    The XCB helpers we need - `xcb_setup_pixmap_formats`, `xcb_randr_get_screen_resources_crtcs`, etc. - return raw C
#    pointers.  ctypes happily converts them to Python objects, but because the conversion went through a plain C
#    call, `_b_base_` never gets filled in.  The GC no longer realizes that the derived array depends on the reply, so
#    once every direct reference to the reply drops, libc is free to `free()` the allocation.  Any later access
#    through the derived pointer becomes undefined behaviour.
#
# 4. How this module keeps everything safe.
#    After every call into an XCB accessor we immediately call `depends_on(child, parent)`.  That helper installs a
#    finalizer on `child` whose only job is to keep a reference to `parent`.  No extra work is performed; the callback
#    holding the reference is enough to keep the reply alive until the child objects disappear.  Separately, when we
#    first receive the reply, we register another finalizer that hands the pointer back to libc once *all* dependants
#    have been collected.  As a result, higher-level code can treat these helper functions just like the XCB C API:
#    grab the array you need, keep it as long as you like, and trust that it stays valid.


def depends_on(subobject: Any, superobject: Any) -> None:
    """Make sure that superobject is not GC'd before subobject.

    In XCB, a structure often is allocated with additional trailing
    data following it, with special accessors to get pointers to that
    extra data.

    In ctypes, if you access a structure field, a pointer value, etc.,
    then the outer object won't be garbage collected until after the
    inner object.  (This uses the ctypes _b_base_ mechanism.)

    However, when using the XCB accessor functions, you don't get that
    guarantee automatically.  Once all references to the outer
    structure have dropped, then we will free the memory for it (the
    response structures XCB returns have to be freed by us), including
    the trailing data.  If there are live references to the trailing
    data, then those will become invalid.

    To prevent this, we use depends_on to make sure that the
    outer structure is not released before all the references to the
    inner objects have been cleared.
    """
    # The implementation is quite simple.  We create a finalizer on the inner object, with a callback that references
    # the outer object.  That ensures that there are live references to the outer object until the references to the
    # inner object have been gc'd.  We can't just create a ref, though; it seems that their callbacks will only run if
    # the ref itself is still referenced.  We need the extra machinery that finalize provides, which uses an internal
    # registry to keep the refs alive.
    finalize(subobject, id, superobject)


#### XCB basic structures


class Connection(Structure):
    pass  # Opaque


class XID(c_uint32):
    pass


class GenericErrorStructure(Structure):
    # The XCB name in C is xcb_generic_error.  It is named differently here to make it clear that this is not an
    # exception class, since in Python, those traditionally end in ...Error.
    _fields_ = (
        ("response_type", c_uint8),
        ("error_code", c_uint8),
        ("sequence", c_uint16),
        ("resource_id", c_uint32),
        ("minor_code", c_uint16),
        ("major_code", c_uint8),
        ("pad0", c_uint8),
        ("pad", c_uint32 * 5),
        ("full_sequence", c_uint32),
    )


#### Request / response handling
#
# The following recaps a lot of what's in the xcb-requests(3) man page, with a few notes about what we're doing in
# this library.
#
# In XCB, when you send a request to the server, the function returns immediately.  You don't get back the server's
# reply; you get back a "cookie".  (This just holds the sequence number of the request.)  Later, you can use that
# cookie to get the reply or error back.
#
# This lets you fire off requests in rapid succession, and then afterwards check the results.  It also lets you do
# other work (like process a screenshot) while a request is in flight (like getting the next screenshot).  This is
# asynchronous processing, and is great for performance.
#
# In this program, we currently don't try to do anything asynchronously, although the design doesn't preclude it.
# (You'd add a synchronous=False flag to the entrypoint wrappers below, and not call .check / .reply, but rather just
# return the cookie.)
#
# XCB has two types of requests.  Void requests don't return anything from the server.  These are things like "create
# a window".  The typed requests do request information from the server.  These are things like "get a window's size".
#
# Void requests all return the same type of cookie.  The only thing you can do with the cookie is check to see if you
# got an error.
#
# Typed requests return a call-specific cookie with the same structure.  They are call-specific so they can be
# type-checked.  (This is the case in both XCB C and in this library.)
#
# XCB has a concept of "checked" or "unchecked" request functions.  By default, void requests are unchecked.  For an
# unchecked function, XCB doesn't do anything to let you know that the request completed successfully.  If there's an
# error, then you need to handle it in your main loop, as a regular event.  We always use the checked versions
# instead, so that we can raise an exception at the right place in the code.
#
# Similarly, typed requests default to checked, but have unchecked versions.  That's just to align their error
# handling with the unchecked void functions; you always need to do something with the cookie so you can get the
# response.
#
# As mentioned, we always use the checked requests; that's unlikely to change, since error-checking with unchecked
# requests requires control of the event loop.
#
# Below are wrappers that set up the request / response functions in ctypes, and define the cookie types to do error
# handling.


class XError(ScreenShotError):
    """Base exception class for anything related to X11.

    This is not prefixed with Xcb to prevent confusion with the XCB
    error structures.
    """


class XProtoError(XError):
    """Exception indicating server-reported errors."""

    def __init__(self, xcb_conn: Connection, xcb_err: GenericErrorStructure) -> None:
        if isinstance(xcb_err, _Pointer):
            xcb_err = xcb_err.contents
        assert isinstance(xcb_err, GenericErrorStructure)  # noqa: S101

        details = {
            "error_code": xcb_err.error_code,
            "sequence": xcb_err.sequence,
            "resource_id": xcb_err.resource_id,
            "minor_code": xcb_err.minor_code,
            "major_code": xcb_err.major_code,
            "full_sequence": xcb_err.full_sequence,
        }

        # xcb-errors is a library to get descriptive error strings, instead of reporting the raw codes.  This is not
        # installed by default on most systems, but is quite helpful for developers.  We use it if it exists, but
        # don't force the matter.  We can't delay this lookup until we format the error message, since the XCB
        # connection may be gone by then.
        if LIB.errors:
            # We don't try to reuse the error context, since it's per-connection, and probably will only be used once.
            ctx = POINTER(XcbErrorsContext)()
            ctx_new_setup = LIB.errors.xcb_errors_context_new(xcb_conn, ctx)
            if ctx_new_setup == 0:
                try:
                    # Some of these may return NULL, but some are guaranteed.
                    ext_name = POINTER(c_char_p)()
                    error_name = LIB.errors.xcb_errors_get_name_for_error(ctx, xcb_err.error_code, ext_name)
                    details["error"] = error_name.decode("ascii", errors="replace")
                    if ext_name:
                        ext_name_str = ext_name.contents.value
                        # I'm pretty sure it'll always be populated if ext_name is set, but...
                        if ext_name_str is not None:
                            details["extension"] = ext_name_str.decode("ascii", errors="replace")
                    major_name = LIB.errors.xcb_errors_get_name_for_major_code(ctx, xcb_err.major_code)
                    details["major_name"] = major_name.decode("ascii", errors="replace")
                    minor_name = LIB.errors.xcb_errors_get_name_for_minor_code(
                        ctx, xcb_err.major_code, xcb_err.minor_code
                    )
                    if minor_name:
                        details["minor_name"] = minor_name.decode("ascii", errors="replace")
                finally:
                    LIB.errors.xcb_errors_context_free(ctx)

        super().__init__("X11 Protocol Error", details=details)

    def __str__(self) -> str:
        msg = super().__str__()
        details = self.details
        error_desc = f"{details['error_code']} ({details['error']})" if "error" in details else details["error_code"]
        major_desc = (
            f"{details['major_code']} ({details['major_name']})" if "major_name" in details else details["major_code"]
        )
        minor_desc = (
            f"{details['minor_code']} ({details['minor_name']})" if "minor_name" in details else details["minor_code"]
        )
        ext_desc = f"\n  Extension:  {details['extension']}" if "extension" in details else ""
        msg += (
            f"\nX Error of failed request:  {error_desc}"
            f"\n  Major opcode of failed request:  {major_desc}"
            f"{ext_desc}"
            f"\n  Minor opcode of failed request:  {minor_desc}"
            f"\n  Resource id in failed request:  {details['resource_id']}"
            f"\n  Serial number of failed request:  {details['full_sequence']}"
        )
        return msg


class CookieBase(Structure):
    """Generic XCB cookie.

    XCB does not export this as a base type.  However, all XCB cookies
    have the same structure, so this encompasses the common structure
    in Python.
    """

    # It's possible to add a finalizer that will raise an exception if a cookie is garbage collected without being
    # disposed of (through discard, check, or reply).  If we ever start using asynchronous requests, then that would
    # be good to add.  But for now, we can trust the wrapper functions to manage the cookies correctly, without the
    # extra overhead of these finalizers.

    _fields_ = (("sequence", c_uint),)

    def discard(self, xcb_conn: Connection) -> None:
        """Free memory associated with this request, and ignore errors."""
        LIB.xcb.xcb_discard_reply(xcb_conn, self.sequence)


class VoidCookie(CookieBase):
    """XCB cookie for requests with no responses.

    This corresponds to xcb_void_cookie_t.
    """

    def check(self, xcb_conn: Connection) -> None:
        """Verify that the function completed successfully.

        This will raise an exception if there is an error.
        """
        err_p = LIB.xcb.xcb_request_check(xcb_conn, self)
        if not err_p:
            return
        err = copy(err_p.contents)
        LIB.c.free(err_p)
        raise XProtoError(xcb_conn, err)


class ReplyCookieBase(CookieBase):
    _xcb_reply_func = None

    def reply(self, xcb_conn: Connection) -> Structure:
        """Wait for and return the server's response.

        The response will be freed (with libc's free) when it, and its
        descendents, are no longer referenced.

        If the server indicates an error, an exception is raised
        instead.
        """
        err_p = POINTER(GenericErrorStructure)()
        assert self._xcb_reply_func is not None  # noqa: S101
        reply_p = self._xcb_reply_func(xcb_conn, self, err_p)
        if err_p:
            # I think this is always NULL, but we can free it.
            if reply_p:
                LIB.c.free(reply_p)
            # Copying the error structure is cheap, and makes memory management easier.
            err_copy = copy(err_p.contents)
            LIB.c.free(err_p)
            raise XProtoError(xcb_conn, err_copy)
        assert reply_p  # noqa: S101

        # It's not known, at this point, how long the reply structure actually is: there may be trailing data that
        # needs to be processed and then freed.  We have to set a finalizer on the reply, so it can be freed when
        # Python is done with it.  The whole dependency tree, though, leads back to this object and its finalizer.
        # Importantly, reply_void_p does not carry a reference (direct or indirect) to reply_p; that would prevent
        # it from ever being freed.
        reply_void_p = c_void_p(addressof(reply_p.contents))
        finalizer = finalize(reply_p, LIB.c.free, reply_void_p)
        finalizer.atexit = False
        return reply_p.contents


def initialize_xcb_typed_func(lib: CDLL, name: str, request_argtypes: list, reply_struct: type) -> None:
    """Set up ctypes for a response-returning XCB function.

    This is only applicable to checked (the default) variants of
    functions that have a response type.

    This arranges for the ctypes function to take the given argtypes.
    The ctypes function will then return an XcbTypedCookie (rather,
    a function-specific subclass of it).  That can be used to call the
    XCB xcb_blahblah_reply function to check for errors and return the
    server's response.
    """

    base_name = name
    title_name = base_name.title().replace("_", "")
    request_func = getattr(lib, name)
    reply_func = getattr(lib, f"{name}_reply")
    # The cookie type isn't used outside this function, so we can just declare it here implicitly.
    cookie_type = type(f"{title_name}Cookie", (ReplyCookieBase,), {"_xcb_reply_func": reply_func})
    request_func.argtypes = request_argtypes
    request_func.restype = cookie_type
    reply_func.argtypes = [POINTER(Connection), cookie_type, POINTER(POINTER(GenericErrorStructure))]
    reply_func.restype = POINTER(reply_struct)


### XCB types


class XcbExtension(Structure):
    _fields_ = (("name", c_char_p), ("global_id", c_int))


class XcbErrorsContext(Structure):
    """A context for using libxcb-errors.

    Create a context with xcb_errors_context_new() and destroy it with
    xcb_errors_context_free(). Except for xcb_errors_context_free(),
    all functions in libxcb-errors are thread-safe and can be called
    from multiple threads at the same time, even on the same context.
    """


#### Types for special-cased functions


class QueryExtensionReply(Structure):
    _fields_ = (
        ("response_type", c_uint8),
        ("pad0", c_uint8),
        ("sequence", c_uint16),
        ("length", c_uint32),
        ("present", c_uint8),
        ("major_opcode", c_uint8),
        ("first_event", c_uint8),
        ("first_error", c_uint8),
    )


#### XCB libraries singleton


class LibContainer:
    """Container for XCB-related libraries.

    There is one instance exposed as the xcb.LIB global.

    You can access libxcb.so as xcb.LIB.xcb, libc as xcb.LIB.c, etc.
    These are not set up until initialize() is called.  It is safe to
    call initialize() multiple times.

    Library accesses through this container return the ctypes CDLL
    object.  There are no smart wrappers (although the return types are
    the cookie classes defined above).  In other words, if you're
    accessing xcb.LIB.xcb.xcb_foo, then you need to handle the .reply()
    calls and such yourself.  If you're accessing the wrapper functions
    in the xcb module xcb.foo, then it will take care of that for you.
    """

    _EXPOSED_NAMES = frozenset(
        {"c", "xcb", "randr", "randr_id", "render", "render_id", "xfixes", "xfixes_id", "errors"}
    )

    def __init__(self) -> None:
        self._lock = RLock()
        self._initializing = False
        self.initialized = False

    def reset(self) -> None:
        with self._lock:
            if self._initializing:
                msg = "Cannot reset during initialization"
                raise RuntimeError(msg)
            self.initialized = False
            for name in self._EXPOSED_NAMES:
                with suppress(AttributeError):
                    delattr(self, name)

    def initialize(self, callbacks: Iterable[Callable[[], None]] = frozenset()) -> None:  # noqa: PLR0915
        # We'll need a couple of generated types, but we have to load them late, since xcbgen requires this library.
        from .xcbgen import Setup  # noqa: PLC0415

        with self._lock:
            if self.initialized:
                # Something else initialized this object while we were waiting for the lock.
                return

            if self._initializing:
                msg = "Cannot load during initialization"
                raise RuntimeError(msg)

            try:
                self._initializing = True

                # We don't use the cached versions that ctypes.cdll exposes as attributes, since other libraries may be
                # doing their own things with these.

                # We use the libc that the current process has loaded, to make sure we get the right version of free().
                # ctypes doesn't document that None is valid as the argument to LoadLibrary, but it does the same thing
                # as a NULL argument to dlopen: it returns the current process and its loaded libraries.  This includes
                # libc.
                self.c = cdll.LoadLibrary(None)  # type: ignore[arg-type]
                self.c.free.argtypes = [c_void_p]
                self.c.free.restype = None

                libxcb_so = ctypes.util.find_library("xcb")
                if libxcb_so is None:
                    msg = "Library libxcb.so not found"
                    raise ScreenShotError(msg)
                self.xcb = cdll.LoadLibrary(libxcb_so)

                self.xcb.xcb_request_check.argtypes = [POINTER(Connection), VoidCookie]
                self.xcb.xcb_request_check.restype = POINTER(GenericErrorStructure)
                self.xcb.xcb_discard_reply.argtypes = [POINTER(Connection), c_uint]
                self.xcb.xcb_discard_reply.restype = None
                self.xcb.xcb_get_extension_data.argtypes = [POINTER(Connection), POINTER(XcbExtension)]
                self.xcb.xcb_get_extension_data.restype = POINTER(QueryExtensionReply)
                self.xcb.xcb_prefetch_extension_data.argtypes = [POINTER(Connection), POINTER(XcbExtension)]
                self.xcb.xcb_prefetch_extension_data.restype = None

                self.xcb.xcb_get_setup.argtypes = [POINTER(Connection)]
                self.xcb.xcb_get_setup.restype = POINTER(Setup)
                self.xcb.xcb_connection_has_error.argtypes = [POINTER(Connection)]
                self.xcb.xcb_connection_has_error.restype = c_int
                self.xcb.xcb_connect.argtypes = [c_char_p, POINTER(c_int)]
                self.xcb.xcb_connect.restype = POINTER(Connection)
                self.xcb.xcb_disconnect.argtypes = [POINTER(Connection)]
                self.xcb.xcb_disconnect.restype = None

                libxcb_randr_so = ctypes.util.find_library("xcb-randr")
                if libxcb_randr_so is None:
                    msg = "Library libxcb-randr.so not found"
                    raise ScreenShotError(msg)
                self.randr = cdll.LoadLibrary(libxcb_randr_so)
                self.randr_id = XcbExtension.in_dll(self.randr, "xcb_randr_id")

                libxcb_render_so = ctypes.util.find_library("xcb-render")
                if libxcb_render_so is None:
                    msg = "Library libxcb-render.so not found"
                    raise ScreenShotError(msg)
                self.render = cdll.LoadLibrary(libxcb_render_so)
                self.render_id = XcbExtension.in_dll(self.render, "xcb_render_id")

                libxcb_xfixes_so = ctypes.util.find_library("xcb-xfixes")
                if libxcb_xfixes_so is None:
                    msg = "Library libxcb-xfixes.so not found"
                    raise ScreenShotError(msg)
                self.xfixes = cdll.LoadLibrary(libxcb_xfixes_so)
                self.xfixes_id = XcbExtension.in_dll(self.xfixes, "xcb_xfixes_id")

                # xcb_errors is an optional library, mostly only useful to developers.  We use the qualified .so name,
                # since it's subject to change incompatibly.
                try:
                    self.errors: CDLL | None = cdll.LoadLibrary("libxcb-errors.so.0")
                except Exception:  # noqa: BLE001
                    self.errors = None
                else:
                    self.errors.xcb_errors_context_new.argtypes = [
                        POINTER(Connection),
                        POINTER(POINTER(XcbErrorsContext)),
                    ]
                    self.errors.xcb_errors_context_new.restype = c_int
                    self.errors.xcb_errors_context_free.argtypes = [POINTER(XcbErrorsContext)]
                    self.errors.xcb_errors_context_free.restype = None
                    self.errors.xcb_errors_get_name_for_major_code.argtypes = [POINTER(XcbErrorsContext), c_uint8]
                    self.errors.xcb_errors_get_name_for_major_code.restype = c_char_p
                    self.errors.xcb_errors_get_name_for_minor_code.argtypes = [
                        POINTER(XcbErrorsContext),
                        c_uint8,
                        c_uint16,
                    ]
                    self.errors.xcb_errors_get_name_for_minor_code.restype = c_char_p
                    self.errors.xcb_errors_get_name_for_error.argtypes = [
                        POINTER(XcbErrorsContext),
                        c_uint8,
                        POINTER(c_char_p),
                    ]
                    self.errors.xcb_errors_get_name_for_error.restype = c_char_p

                for x in callbacks:
                    x()

            finally:
                self._initializing = False

            self.initialized = True


LIB = LibContainer()


#### Trailing data accessors
#
# In X11, many replies have the header (the *Reply structures defined above), plus some variable-length data after it.
# For instance, XcbScreen includes a list of XcbDepth structures.
#
# These mostly follow two patterns.
#
# For objects with a constant size, we get a pointer and length (count), cast to an array, and return the array
# contents.  (This doesn't involve copying any data.)
#
# For objects with a variable size, we use the XCB-provided iterator protocol to iterate over them, and return a
# Python list.  (This also doesn't copy any data, but does construct a list.)  To continue the example of how
# XcbScreen includes a list of XcbDepth structures: a full XcbDepth is variable-length because it has a variable
# number of visuals attached to it.
#
# These lists with variable element sizes follow a standard pattern:
#
# * There is an iterator class (such as XcbScreenIterator), based on the type you're iterating over.  This defines a
#   data pointer to point to the current object, and a rem counter indicating the remaining number of objects.
# * There is a function to advance the iterator (such as xcb_screen_next), based on the type of iterator being
#   advanced.
# * There is an initializer function (such as xcb_setup_roots_iterator) that takes the container (XcbSetup), and
#   returns an iterator (XcbScreenIterator) pointing to the first object in the list.  (This iterator is returned by
#   value, so Python can free it normally.)
#
# The returned structures are actually part of the allocation of the parent pointer: the POINTER(XcbScreen) objects
# point to objects that were allocated along with the XcbSetup that we got them from.  That means that it is very
# important that the XcbSetup not be freed until the pointers that point into it are freed.


### Iteration utility primitives


def list_from_xcb(iterator_factory: Callable, next_func: Callable, parent: Structure | _Pointer) -> list:
    iterator = iterator_factory(parent)
    items: list = []
    while iterator.rem != 0:
        current = iterator.data.contents
        # Keep the parent reply alive until consumers drop this entry.
        depends_on(current, parent)
        items.append(current)
        next_func(iterator)
    return items


def array_from_xcb(pointer_func: Callable, length_func: Callable, parent: Structure | _Pointer) -> Array:
    pointer = pointer_func(parent)
    length = length_func(parent)
    if length and not pointer:
        msg = "XCB returned a NULL pointer for non-zero data length"
        raise ScreenShotError(msg)
    array_ptr = cast(pointer, POINTER(pointer._type_ * length))
    array = array_ptr.contents
    depends_on(array, parent)
    return array
