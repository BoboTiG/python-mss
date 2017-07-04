=======
MSS API
=======

Classes
=======

GNU/Linux
---------

.. module:: mss.linux

.. class:: MSS

    .. method:: __init__(display=None)

        :param: str display: display to use.

        GNU/Linux initializations.

    .. method:: grab(monitor) -> ScreenShot

        :exception ScreenShotError: When color depth is not 32 (rare).

        See :attr:`mss.base.MSSBase.grab` for details.


Methods
=======

.. module:: mss.base

.. class:: MSSBase

    The parent's class for every OS implementation.

    .. method:: grab(monitor) -> ScreenShot

        :param dict monitor: monitor's informations.
        :exception NotImplementedError: Subclasses need to implement this.

        Retrieve screen pixels for a given monitor.

    .. method:: save(mon=0, output='monitor-%d.png', callback=None) -> generator

        :param int mon: the monitor's number.
        :param str output: the output's file name. ``%d``, if present, will be replaced by the monitor number.
        :param callable callback: callback called before saving the screenshot to a file. Takes the ``output`` argument as parameter.

        Grab a screenshot and save it to a file. This is a generator which returns created files.

.. class:: ScreenShot

    Screen shot object.

    .. note::

        A better name would be *Image*, but to prevent collisions
        with ``PIL.Image``, it has been decided to use another name.

    .. classmethod:: from_size(cls, data, width, height) -> ScreenShot

        :param bytearray data: raw BGRA pixels retrieved by ctype
                               OS independent implementations.
        :param int width: the monitor's width.
        :param int height: the monitor's height.

        Instanciate a new class given only screenshot's data and size.

    .. method:: pixels(coord_x, coord_y) -> Tuple[int, int, int]

        : param coord_x int: The x coordinate.
        : param coord_y int: The y coordinate.

        Get the pixel value at the given position.

.. module:: mss.tools

    .. method:: to_png(data, size, output) -> None

    :param bytes data: RGBRGB...RGB data.
    :param tuple size: The (width, height) pair.
    :param str output: output's file name.
    :exception ScreenShotError: On error when writing ``data`` to ``output``.

    Dump data to the image file. Pure Python PNG implementation.


Properties
==========

.. class:: MSSBase

    .. attribute:: monitors

        :type:  List[Dict[str, int]]
        Positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill ``self._monitors`` with all informations
        and use it as a cache:
            ``self._monitors[0]`` is a dict of all monitors together
            ``self._monitors[N]`` is a dict of the monitor N (with N > 0)

        Each monitor is a dict with:
        {
            'left':   the x-coordinate of the upper-left corner,
            'top':    the y-coordinate of the upper-left corner,
            'width':  the width,
            'height': the height
        }

.. class:: ScreenShot

    .. attribute:: __array_interface__()

        :type: dict[str, Any]
        Numpy array interface support. It uses raw data in BGRA form.

    .. attribute:: pos

        :type: NamedTuple
        The screen shot's coodinates.

    .. attribute:: top

        :type: int
        The screen shot's top coodinate.

    .. attribute:: left

        :type: int
        The screen shot's left coodinate.

    .. attribute:: size

        :type: NamedTuple
        The screen shot's size.

    .. attribute:: width

        :type: int
        The screen shot's width.

    .. attribute:: height

        :type: int
        The screen shot's height.

    .. attribute:: pixels

        :type: List[Tuple[int, int, int]]
        List of RGB tuples.

    .. attribute:: rgb

        :type: bytes
        Compute RGB values from the BGRA raw pixels.


Exception
=========

.. module:: mss.exception

.. exception:: ScreenShotError

    Base class for MSS exceptions.


Factory
=======

.. module:: mss.factory

.. function:: mss() -> MSSBase

    Factory function to instance the appropriate MSS class.
