6.1.0 (2020-10-31)
==================

darwin.py
---------
 - Added ``CFUNCTIONS``

linux.py
--------
 - Added ``CFUNCTIONS``

windows.py
----------
 - Added ``CFUNCTIONS``
 - Added ``MONITORNUMPROC``
 - Removed ``MSS.monitorenumproc``. Use ``MONITORNUMPROC`` instead.


6.0.0 (2020-06-30)
==================

base.py
-------
 - Added ``lock``
 - Added ``MSS._grab_impl()`` (abstract method)
 - Added ``MSS._monitors_impl()`` (abstract method)
 - ``MSS.grab()`` is no more an abstract method
 - ``MSS.monitors`` is no more an abstract property

darwin.py
---------
 - Renamed ``MSS.grab()`` to ``MSS._grab_impl()``
 - Renamed ``MSS.monitors`` to ``MSS._monitors_impl()``

linux.py
--------
 - Added ``MSS.has_extension()``
 - Removed ``MSS.display``
 - Renamed ``MSS.grab()`` to ``MSS._grab_impl()``
 - Renamed ``MSS.monitors`` to ``MSS._monitors_impl()``

windows.py
----------
 - Removed ``MSS._lock``
 - Renamed ``MSS.srcdc_dict`` to ``MSS._srcdc_dict``
 - Renamed ``MSS.grab()`` to ``MSS._grab_impl()``
 - Renamed ``MSS.monitors`` to ``MSS._monitors_impl()``


5.1.0 (2020-04-30)
==================

base.py
-------
- Renamed back ``MSSMixin`` class to ``MSSBase``
- ``MSSBase`` is now derived from ``abc.ABCMeta``
- ``MSSBase.monitor`` is now an abstract property
- ``MSSBase.grab()`` is now an abstract method

windows.py
----------
 - Replaced ``MSS.srcdc`` with ``MSS.srcdc_dict``


5.0.0 (2019-12-31)
==================

darwin.py
---------
- Added `MSS.__slots__`

linux.py
--------
- Added `MSS.__slots__`
- Deleted `MSS.close()`
- Deleted ``LAST_ERROR`` constant. Use ``ERROR`` namespace instead, specially the ``ERROR.details`` attribute.

models.py
---------
- Added ``Monitor``
- Added ``Monitors``
- Added ``Pixel``
- Added ``Pixels``
- Added ``Pos``
- Added ``Size``

screenshot.py
-------------
- Added `ScreenShot.__slots__`
- Removed ``Pos``. Use ``models.Pos`` instead.
- Removed ``Size``. Use ``models.Size`` instead.

windows.py
----------
- Added `MSS.__slots__`
- Deleted `MSS.close()`


4.0.1 (2019-01-26)
==================

linux.py
--------
- Removed use of ``MSS.xlib.XDefaultScreen()``


4.0.0 (2019-01-11)
==================

base.py
-------
- Renamed ``MSSBase`` class to ``MSSMixin``

linux.py
--------
- Renamed ``MSS.__del__()`` method to ``MSS.close()``
- Deleted ``MSS.last_error`` attribute. Use ``LAST_ERROR`` constant instead.
- Added ``validate()`` function
- Added ``MSS.get_error_details()`` method

windows.py
----------
- Renamed ``MSS.__exit__()`` method to ``MSS.close()``


3.3.0 (2018-09-04)
==================

exception.py
------------
- Added ``details`` attribute to ``ScreenShotError`` exception. Empty dict by default.

linux.py
--------
- Added ``error_handler()`` function


3.2.1 (2018-05-21)
==================

windows.py
----------
- Removed ``MSS.scale_factor`` property
- Removed ``MSS.scale()`` method


3.2.0 (2018-03-22)
==================

base.py
-------
- Added ``MSSBase.compression_level`` to control the PNG compression level

linux.py
--------
- Added ``MSS.drawable`` to speed-up grabbing.

screenshot.py
-------------
- Added ``Screenshot.bgra`` to get BGRA bytes.

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
- Removed ``_crop_width()`` method. Screen shots are now using the width set by the OS (rounded to 16).

exception.py
------------
- Renamed ``ScreenshotError`` class to ``ScreenShotError``

tools.py
--------
- Changed signature of ``to_png(data, monitor, output)`` to ``to_png(data, size, output)`` where ``size`` is a ``tuple(width, height)``
