=======
MSS API
=======

Classes
=======

macOS
-----

.. module:: mss.darwin

.. attribute:: CFUNCTIONS

    .. versionadded:: 6.1.0

.. function:: cgfloat

.. class:: CGPoint

.. class:: CGSize

.. class:: CGRect

.. class:: MSS

    .. attribute:: core

    .. attribute:: max_displays

GNU/Linux
---------

.. module:: mss.linux

Factory function to return the appropriate backend implementation.

.. function:: mss(backend="default", **kwargs)

    :keyword str backend: Backend name ("default", "xlib", "xgetimage", or "xshmgetimage").
    :keyword display: Display name (e.g., ":0.0") for the X server.  Default is taken from the :envvar:`DISPLAY` environment variable.
    :type display: str or None
    :param kwargs: Additional arguments passed to the backend MSS class.
    :rtype: :class:`mss.base.MSSBase`
    :return: Backend-specific MSS instance.

    Factory returning a proper MSS class instance for GNU/Linux.
    The backend parameter selects the implementation:

    - "default" or "xshmgetimage": XCB-based backend using XShmGetImage (default, with automatic fallback to XGetImage)
    - "xgetimage": XCB-based backend using XGetImage
    - "xlib": Traditional Xlib-based backend retained for environments without working XCB libraries

.. function:: MSS(*args, **kwargs)

    Alias for :func:`mss` for backward compatibility.


Xlib Backend
^^^^^^^^^^^^

.. module:: mss.linux.xlib

Legacy Xlib-based backend, kept as a fallback when XCB is unavailable.

.. attribute:: CFUNCTIONS

    .. versionadded:: 6.1.0

.. attribute:: PLAINMASK

.. attribute:: ZPIXMAP

.. class:: Display

    Structure that serves as the connection to the X server, and that contains all the information about that X server.

.. class:: XErrorEvent

    XErrorEvent to debug eventual errors.

.. class:: XFixesCursorImage

    Cursor structure

.. class:: XImage

    Description of an image as it exists in the client's memory.

.. class:: XRRCrtcInfo

    Structure that contains CRTC information.

.. class:: XRRModeInfo

.. class:: XRRScreenResources

    Structure that contains arrays of XIDs that point to the available outputs and associated CRTCs.

.. class:: XWindowAttributes

    Attributes for the specified window.

.. class:: MSS

    .. method:: close()

        Clean-up method.

        .. versionadded:: 8.0.0


XGetImage Backend
^^^^^^^^^^^^^^^^^

.. module:: mss.linux.xgetimage

XCB-based backend using XGetImage protocol.

.. class:: MSS

    XCB implementation using XGetImage for screenshot capture.


XShmGetImage Backend
^^^^^^^^^^^^^^^^^^^^

.. module:: mss.linux.xshmgetimage

XCB-based backend using XShmGetImage protocol with shared memory.

.. class:: ShmStatus

    Enum describing the availability of the X11 MIT-SHM extension used by the backend.

    .. attribute:: UNKNOWN

        Initial state before any capture confirms availability or failure.

    .. attribute:: AVAILABLE

        Shared-memory capture works and will continue to be used.

    .. attribute:: UNAVAILABLE

        Shared-memory capture failed; MSS will use XGetImage.

.. class:: MSS

    XCB implementation using XShmGetImage for screenshot capture.
    Falls back to XGetImage if shared memory extension is unavailable.

    .. attribute:: shm_status

        Current shared-memory availability, using :class:`mss.linux.xshmgetimage.ShmStatus`.

    .. attribute:: shm_fallback_reason

        Optional string describing why the backend fell back to XGetImage when MIT-SHM is unavailable.

Windows
-------

.. module:: mss.windows

.. attribute:: CAPTUREBLT

.. attribute:: CFUNCTIONS

    .. versionadded:: 6.1.0

.. attribute:: DIB_RGB_COLORS

.. attribute:: SRCCOPY

.. class:: BITMAPINFOHEADER

.. class:: BITMAPINFO

.. attribute:: MONITORNUMPROC

    .. versionadded:: 6.1.0

.. class:: MSS

    .. attribute:: gdi32

    .. attribute:: user32

Methods
=======

.. module:: mss.base

.. attribute:: lock

    .. versionadded:: 6.0.0

.. class:: MSSBase

    The parent's class for every OS implementation.

    .. attribute:: cls_image

    .. attribute:: compression_level

        PNG compression level used when saving the screenshot data into a file (see :py:func:`zlib.compress()` for details).

        .. versionadded:: 3.2.0

    .. attribute:: with_cursor

        Include the mouse cursor in screenshots.

        .. versionadded:: 8.0.0

    .. method:: __init__(compression_level=6, display=None, max_displays=32, with_cursor=False)

        :type compression_level: int
        :param compression_level: PNG compression level.
        :type display: bytes, str or None
        :param display: The display to use. Only effective on GNU/Linux.
        :type max_displays: int
        :param max_displays: Maximum number of displays. Only effective on macOS.
        :type with_cursor: bool
        :param with_cursor: Include the mouse cursor in screenshots.

        .. versionadded:: 8.0.0
            ``compression_level``, ``display``, ``max_displays``, and ``with_cursor``, keyword arguments.

    .. method:: close()

        Clean-up method.

        .. versionadded:: 4.0.0

    .. method:: grab(region)

        :param dict monitor: region's coordinates.
        :rtype: :class:`ScreenShot`

        Retrieve screen pixels for a given *region*.
        Subclasses need to implement this.

        .. note::

            *monitor* can be a ``tuple`` like ``PIL.Image.grab()`` accepts,
            it will be converted to the appropriate ``dict``.

    .. method:: save([mon=1], [output='mon-{mon}.png'], [callback=None])

        :param int mon: the monitor's number.
        :param str output: the output's file name.
        :type callback: callable or None
        :param callback: callback called before saving the screenshot to a file. Takes the *output* argument as parameter.
        :rtype: iterable
        :return: Created file(s).

        Grab a screenshot and save it to a file.
        The *output* parameter can take several keywords to customize the filename:

            - ``{mon}``: the monitor number
            - ``{top}``: the screenshot y-coordinate of the upper-left corner
            - ``{left}``: the screenshot x-coordinate of the upper-left corner
            - ``{width}``: the screenshot's width
            - ``{height}``: the screenshot's height
            - ``{date}``: the current date using the default formatter

        As it is using the :py:func:`format()` function, you can specify formatting options like ``{date:%Y-%m-%s}``.

        .. warning:: On Windows, the default date format may result with a filename containing ':' which is not allowed::

                IOerror: [Errno 22] invalid mode ('wb') or filename: 'sct_1-2019-01-01 21:20:43.114194.png'

            To fix this, you must provide a custom date formatting.

    .. method:: shot()

        :return str: The created file.

        Helper to save the screenshot of the first monitor, by default.
        You can pass the same arguments as for :meth:`save()`.

        .. versionadded:: 3.0.0

.. class:: ScreenShot

    Screenshot object.

    .. note::

        A better name would have been *Image*, but to prevent collisions
        with ``PIL.Image``, it has been decided to use *ScreenShot*.

    .. classmethod:: from_size(cls, data, width, height)

        :param bytearray data: raw BGRA pixels retrieved by ctypes
                               OS independent implementations.
        :param int width: the monitor's width.
        :param int height: the monitor's height.
        :rtype: :class:`ScreenShot`

        Instantiate a new class given only screenshot's data and size.

    .. method:: pixel(coord_x, coord_y)

        :param int coord_x: The x coordinate.
        :param int coord_y: The y coordinate.
        :rtype: tuple(int, int, int)

        Get the pixel value at the given position.

        .. versionadded:: 3.0.0

.. module:: mss.tools

.. method:: to_png(data, size, level=6, output=None)

    :param bytes data: RGBRGB...RGB data.
    :param tuple size: The (width, height) pair.
    :param int level: PNG compression level.
    :param str output: output's file name.
    :raises ScreenShotError: On error when writing *data* to *output*.
    :raises zlib.error: On bad compression *level*.

    Dump data to the image file. Pure Python PNG implementation.
    If *output* is ``None``, create no file but return the whole PNG data.

    .. versionadded:: 3.0.0

    .. versionchanged:: 3.2.0

        The *level* keyword argument to control the PNG compression level.


Properties
==========

.. class:: mss.base.MSSBase

    .. attribute:: monitors

        Positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill ``self._monitors`` with all information
        and use it as a cache:

        - ``self._monitors[0]`` is a dict of all monitors together
        - ``self._monitors[N]`` is a dict of the monitor N (with N > 0)

        Each monitor is a dict with:

        - ``left``: the x-coordinate of the upper-left corner
        - ``top``: the y-coordinate of the upper-left corner
        - ``width``: the width
        - ``height``: the height

        Subclasses need to implement this.

        :rtype:  list[dict[str, int]]

.. class:: mss.base.ScreenShot

    .. attribute:: __array_interface__()

        Numpy array interface support. It uses raw data in BGRA form.

        :rtype: dict[str, Any]

    .. attribute:: bgra

        BGRA values from the BGRA raw pixels.

        :rtype: bytes

        .. versionadded:: 3.2.0

    .. attribute:: height

        The screenshot's height.

        :rtype: int

    .. attribute:: left

        The screenshot's left coordinate.

        :rtype: int

    .. attribute:: pixels

        List of row tuples that contain RGB tuples.

        :rtype: list[tuple(tuple(int, int, int), ...)]

    .. attribute:: pos

        The screenshot's coordinates.

        :rtype: :py:func:`collections.namedtuple()`

    .. attribute:: rgb

        Computed RGB values from the BGRA raw pixels.

        :rtype: bytes

        .. versionadded:: 3.0.0

    .. attribute:: size

        The screenshot's size.

        :rtype: :py:func:`collections.namedtuple()`

    .. attribute:: top

        The screenshot's top coordinate.

        :rtype: int

    .. attribute:: width

        The screenshot's width.

        :rtype: int


Exception
=========

.. module:: mss.exception

.. exception:: ScreenShotError

    Base class for MSS exceptions.

    .. attribute:: details

        On GNU/Linux, and if the error comes from the XServer, it contains XError details.
        This is an empty dict by default.

        For XErrors, you can find information on `Using the Default Error Handlers <https://tronche.com/gui/x/xlib/event-handling/protocol-errors/default-handlers.html>`_.

        :rtype: dict[str, Any]

        .. versionadded:: 3.3.0


Factory
=======

.. module:: mss.factory

.. function:: mss()

    Factory function to instance the appropriate MSS class.
