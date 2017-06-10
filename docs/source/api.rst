=======
MSS API
=======

Classes
=======

``MSSBase`` is the parent's class for every OS implementation.


GNU/Linux
---------

.. module:: mss.linux

.. class:: MSS

    .. method:: __init__(display=None)

        :param: str display: display to use.

        GNU/Linux initializations.


    .. method:: get_pixels(monitor) -> bytes

        :exception ScreenshotError: When color depth is not 32 (rare).

        See :attr:`mss.base.MSSBase.get_pixels` for details.


Methods
=======

.. module:: mss.base

.. class:: MSSBase

    .. method:: bgra_to_rgb(raw) -> bytes

        :param bytearray raw: raw data containing BGRA values.

        It converts pixels values from BGRA to RGB.
        This is the method called to populate :attr:`image` into :attr:`get_pixels`.


    .. method:: get_pixels(monitor) -> bytes

        :param dict monitor: monitor's informations.
        :exception NotImplementedError: Subclasses need to implement this.

        Retrieve screen pixels for a given monitor.
        This method has to define :attr:`width` and :attr:`height`.
        It stocks pixels data into :attr:`image` (RGB) and returns it.


    .. method:: save(mon=0, output='monitor-%d.png', callback=None) -> generator

        :param int mon: the monitor's number.
        :param str output: the output's file name. ``%d``, if present, will be replaced by the monitor number.
        :param callable callback: callback called before saving the screenshot to a file. Takes the ``output`` argument as parameter.

        Grab a screenshot and save it to a file. This is a generator which returns created files.


    .. method:: to_png(data, output) -> None

        :param bytes data: raw pixels (RGBRGB...RGB) fom :attr:`get_pixels()`.
        :param str output: output's file name.
        :exception ScreenshotError: On error when writing ``data`` to ``output``.

        Dump data to the image file. Pure Python PNG implementation.


    .. method:: enum_display_monitors(force=False) -> list(dict)

        .. deprecated:: 2.1.0

        Use :attr:`monitors` instead.


Attributes
==========

.. class:: MSSBase

    .. attribute:: image

        :getter: Raw pixels of a monitor.
        :setter: See :attr:`get_pixels`.
        :type: bytes


    .. attribute:: monitors

        :getter: The list of all monitors.
        :type: list(dict)

        Get positions of one or more monitors.
        If the monitor has rotation, you have to deal with it inside this method.

        This method has to fill ``__monitors`` with all informations and use it as a cache:

        - ``__monitors[0]`` is a dict of all monitors together;
        - ``__monitors[N]`` is a dict of the monitor N (with N > 0).

        Each monitor is a dict with::

            {
                'left':   the x-coordinate of the upper-left corner,
                'top':    the y-coordinate of the upper-left corner,
                'width':  the width,
                'height': the height
            }


    .. attribute:: width

        :getter: Width of a monitor.
        :setter: See :attr:`get_pixels()`.
        :type: int


    .. attribute:: height

        :getter: Height of a monitor.
        :setter: See :attr:`get_pixels()`.
        :type: int


Exception
=========

.. module:: mss.exception

.. exception:: ScreenshotError

    Base class for MSS exceptions.


Factory
=======

.. module:: mss.factory

.. function:: mss() -> MSSBase

    Factory function to instance the appropriate MSS class.
