=======
MSS API
=======

Classes
=======

GNU/Linux
---------

.. module:: mss.linux

.. class:: MSS

    .. method:: __init__([display=None])

        :type display: str or None
        :param display: The display to use.

        GNU/Linux initializations.

    .. method:: close()

        Disconnect from the X server.

        .. versionadded:: 4.0.0

    .. method:: grab(monitor)

        :rtype: :class:`mss.base.ScreenShot`
        :raises ScreenShotError: When color depth is not 32 (rare).

        See :meth:`mss.base.MSSMixin.grab()` for details.

.. function:: error_handler(display, event)

    :type display: ctypes.POINTER(Display)
    :param display: The display impacted by the error.
    :type event: ctypes.POINTER(Event)
    :param event: XError details.
    :return int: Always ``0``.

    Error handler passed to `X11.XSetErrorHandler()` to catch any error that can happen when calling a X11 function.
    This will prevent Python interpreter crashes.

    When such an error happen, a :class:`mss.exception.ScreenShotError` exception is raised and all XError information are added to the :attr:`mss.exception.ScreenShotError.details` attribute.

    .. versionadded:: 3.3.0


Windows
-------

.. module:: mss.windows

.. class:: MSS

    .. method:: close()

        Close GDI handles and free DCs.

        .. versionadded:: 4.0.0


Methods
=======

.. module:: mss.base

.. class:: MSSMixin

    The parent's class for every OS implementation.

    .. method:: close()

        Clean-up method. Does nothing by default.

        .. versionadded:: 4.0.0

    .. method:: grab(region)

        :param dict monitor: region's coordinates.
        :rtype: :class:`ScreenShot`
        :raises NotImplementedError: Subclasses need to implement this.

        Retrieve screen pixels for a given *region*.

        .. note::

            *monitor* can be a ``tuple`` like ``PIL.Image.grab()`` accepts,
            it will be converted to the appropriate ``dict``.

    .. method:: save([mon=1], [output='mon-{mon}.png'], [callback=None])

        :param int mon: the monitor's number.
        :param str output: the output's file name.
        :type callback: callable or None
        :param callback: callback called before saving the screen shot to a file. Takes the *output* argument as parameter.
        :rtype: iterable
        :return: Created file(s).

        Grab a screen shot and save it to a file.
        The *output* parameter can take several keywords to customize the filename:

            - ``{mon}``: the monitor number
            - ``{top}``: the screen shot y-coordinate of the upper-left corner
            - ``{left}``: the screen shot x-coordinate of the upper-left corner
            - ``{width}``: the screen shot's width
            - ``{height}``: the screen shot's height
            - ``{date}``: the current date using the default formatter

        As it is using the :py:func:`format()` function, you can specify formatting options like ``{date:%Y-%m-%s}``.

    .. method:: shot()

        :return str: The created file.

        Helper to save the screen shot of the first monitor, by default.
        You can pass the same arguments as for :meth:`save()`.

        .. versionadded:: 3.0.0

.. class:: ScreenShot

    Screen shot object.

    .. note::

        A better name would have been *Image*, but to prevent collisions
        with ``PIL.Image``, it has been decided to use *ScreenShot*.

    .. classmethod:: from_size(cls, data, width, height)

        :param bytearray data: raw BGRA pixels retrieved by ctypes
                               OS independent implementations.
        :param int width: the monitor's width.
        :param int height: the monitor's height.
        :rtype: :class:`ScreenShot`

        Instantiate a new class given only screen shot's data and size.

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

    .. versionadded:: 3.2.0

        The *level* keyword argument to control the PNG compression level.


Properties
==========

.. module:: mss.base

.. class:: MSSMixin

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

        :rtype:  list[dict[str, int]]

.. class:: ScreenShot

    .. attribute:: __array_interface__()

        Numpy array interface support. It uses raw data in BGRA form.

        :rtype: dict[str, Any]

    .. attribute:: bgra

        BGRA values from the BGRA raw pixels.

        :rtype: bytes

        .. versionadded:: 3.2.0

    .. attribute:: height

        The screen shot's height.

        :rtype: int

    .. attribute:: left

        The screen shot's left coordinate.

        :rtype: int

    .. attribute:: pixels

        List of RGB tuples.

        :rtype: list[tuple(int, int, int)]

    .. attribute:: pos

        The screen shot's coordinates.

        :rtype: :py:func:`collections.namedtuple()`

    .. attribute:: rgb

        Computed RGB values from the BGRA raw pixels.

        :rtype: bytes

        .. versionadded:: 3.0.0

    .. attribute:: size

        The screen shot's size.

        :rtype: :py:func:`collections.namedtuple()`

    .. attribute:: top

        The screen shot's top coordinate.

        :rtype: int

    .. attribute:: width

        The screen shot's width.

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

    :rtype: :class:`mss.base.MSSMixin`
