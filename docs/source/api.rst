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
        :rtype: ScreenShot

        See :attr:`mss.base.MSSBase.grab` for details.


Methods
=======

.. module:: mss.base

.. class:: MSSBase

    The parent's class for every OS implementation.

    .. method:: grab(monitor) -> ScreenShot

        :param dict monitor: monitor's informations.
        :exception NotImplementedError: Subclasses need to implement this.
        :rtype: ScreenShot

        Retrieve screen pixels for a given monitor.

    .. method:: save(mon=0, output='monitor-%d.png', callback=None) -> generator

        :param int mon: the monitor's number.
        :param str output: the output's file name. ``%d``, if present, will be replaced by the monitor number.
        :param callable callback: callback called before saving the screenshot to a file. Takes the ``output`` argument as parameter.
        :rtype: generator

        Grab a screenshot and save it to a file. This is a generator which returns created files.

.. class:: ScreenShot

    Screen shot object.

    .. note::

        A better name would have been *Image*, but to prevent collisions
        with ``PIL.Image``, it has been decided to use *ScreenShot*.

    .. classmethod:: from_size(cls, data, width, height) -> ScreenShot

        :param bytearray data: raw BGRA pixels retrieved by ctype
                               OS independent implementations.
        :param int width: the monitor's width.
        :param int height: the monitor's height.
        :rtype: ScreenShot

        Instanciate a new class given only screenshot's data and size.

    .. method:: pixels(coord_x, coord_y) -> Tuple[int, int, int]

        :param int coord_x: The x coordinate.
        :param int coord_y: The y coordinate.
        :rtype: Tuple[int, int, int]

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

        Positions of all monitors.
        If the monitor has rotation, you have to deal with it
        inside this method.

        This method has to fill ``self._monitors`` with all informations
        and use it as a cache:

        - ``self._monitors[0]`` is a dict of all monitors together
        - ``self._monitors[N]`` is a dict of the monitor N (with N > 0)

        Each monitor is a dict with:

        - ``left``: the x-coordinate of the upper-left corner
        - ``top``: the y-coordinate of the upper-left corner
        - ``width``: the width
        - ``height``: the height

        :type:  List[Dict[str, int]]

.. class:: ScreenShot

    .. attribute:: __array_interface__()

        Numpy array interface support. It uses raw data in BGRA form.

        :type: Dict[str, Any]

    .. attribute:: pos

        The screen shot's coodinates.

        :type: NamedTuple

    .. attribute:: top

        The screen shot's top coodinate.

        :type: int

    .. attribute:: left

        The screen shot's left coodinate.
        :type: int

    .. attribute:: size

        The screen shot's size.

        :type: NamedTuple

    .. attribute:: width

        The screen shot's width.

        :type: int

    .. attribute:: height

        The screen shot's height.

        :type: int

    .. attribute:: pixels

        List of RGB tuples.

        :type: List[Tuple[int, int, int]]

    .. attribute:: rgb

        Computed RGB values from the BGRA raw pixels.

        :type: bytes


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
