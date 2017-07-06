3.0.0 (2017-07-06)
==================

base.py
-------
- Added the `ScreenShot` class containing data for a given screen shot (support the Numpy array interface [`ScreenShot.__array_interface__`])
- Add `shot()` method to `MSSBase`. It takes the same arguments as the `save()` method.
- Renamed `get_pixels` to `grab`. It now returns a `ScreenShot` object.
- Moved `to_png` method to `tools.py`. It is now a simple function.
- Removed `enum_display_monitors()` method. Use `monitors` property instead.
- Removed `monitors` attribute. Use `monitors` property instead.
- Removed `width` attribute. Use `ScreenShot.size[0]` attribute or `ScreenShot.width` property instead.
- Removed `height` attribute. Use `ScreenShot.size[1]` attribute or `ScreenShot.height` property instead.
- Removed `image`. Use the `ScreenShot.raw` attribute or `ScreenShot.rgb` property instead.
- Removed `bgra_to_rgb()` method. Use `ScreenShot.rgb` property instead.

darwin.py
---------
- Removed `_crop_width()` method. Screen shots are now using the width setted by the OS (rounded to 16).

exception.py
------------
- Renamed `ScreenshotError` class to `ScreenShotError`

tools.py
--------
- Changed signature of `to_png(data, monitor, output)` to `to_png(data, size, output)` where `size` is a `tuple(width, height)`
