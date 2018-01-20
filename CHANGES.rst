3.1.3 (2018-xx-xx)
==================

base.py
-------
- Added ``MSSBase.compression_level`` to control the PNG compression level

tools.py
--------
- Changed signature of ``to_png(data, size, output=None)`` to ``to_png(data, size, level=6, output=None)``. ``level`` is the Zlib compression level.


3.1.2 (2018-01-05)
==================

tools.py
--------
- Changed signature of ``to_png(data, size, output)`` to ``to_png(data, size, output=None)``. If ``output`` is ``None``, the raw PNG bytes will be returned.


3.1.1 (2017-11-27)
==================

__main__.py
-----------
- Added ``args`` argument to ``main()``

base.py
-------
- Moved ``ScreenShot`` class to screenshot.py

darwin.py
---------
- Added ``CGPoint.__repr__()``
- Added ``CGRect.__repr__()``
- Added ``CGSize.__repr__()``
- Removed ``get_infinity()`` function

windows.py
----------
- Added ``scale()`` method to ``MSS`` class
- Added ``scale_factor`` property to ``MSS`` class


3.0.0 (2017-07-06)
==================

base.py
-------
- Added the ``ScreenShot`` class containing data for a given screen shot (support the Numpy array interface [``ScreenShot.__array_interface__``])
- Added ``shot()`` method to ``MSSBase``. It takes the same arguments as the ``save()`` method.
- Renamed ``get_pixels`` to ``grab``. It now returns a ``ScreenShot`` object.
- Moved ``to_png`` method to ``tools.py``. It is now a simple function.
- Removed ``enum_display_monitors()`` method. Use ``monitors`` property instead.
- Removed ``monitors`` attribute. Use ``monitors`` property instead.
- Removed ``width`` attribute. Use ``ScreenShot.size[0]`` attribute or ``ScreenShot.width`` property instead.
- Removed ``height`` attribute. Use ``ScreenShot.size[1]`` attribute or ``ScreenShot.height`` property instead.
- Removed ``image``. Use the ``ScreenShot.raw`` attribute or ``ScreenShot.rgb`` property instead.
- Removed ``bgra_to_rgb()`` method. Use ``ScreenShot.rgb`` property instead.

darwin.py
---------
- Removed ``_crop_width()`` method. Screen shots are now using the width setted by the OS (rounded to 16).

exception.py
------------
- Renamed ``ScreenshotError`` class to ``ScreenShotError``

tools.py
--------
- Changed signature of ``to_png(data, monitor, output)`` to ``to_png(data, size, output)`` where ``size`` is a ``tuple(width, height)``
