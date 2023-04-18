# Technical Changes

## 9.0.0 (2023-04-18)

### linux.py
- Removed `XEvent` class. Use `XErrorEvent` instead.

### windows.py
- Added `MSS.close()` method
- Removed `MSS.bmp` attribute
- Removed `MSS.memdc` attribute

## 8.0.3 (2023-04-15)

### linux.py
- Added `XErrorEvent` class (old `Event` class is just an alias now, and will be removed in v9.0.0)

## 8.0.0 (2023-04-09)

### base.py
- Added `compression_level=6` keyword argument to `MSS.__init__()`
- Added `display=None` keyword argument to `MSS.__init__()`
- Added `max_displays=32` keyword argument to `MSS.__init__()`
- Added `with_cursor=False` keyword argument to `MSS.__init__()`
- Added `MSS.with_cursor` attribute

### linux.py
- Added `MSS.close()`
- Moved `MSS.__init__()` keyword arguments handling to the base class
- Renamed `error_handler()` function to `_error_handler()`
- Renamed `validate()` function to `__validate()`
- Renamed `MSS.has_extension()` method to `_is_extension_enabled()`
- Removed `ERROR` namespace
- Removed `MSS.drawable` attribute
- Removed `MSS.root` attribute
- Removed `MSS.get_error_details()` method. Use `ScreenShotError.details` attribute instead.

## 6.1.0 (2020-10-31)

### darwin.py
- Added `CFUNCTIONS`

### linux.py
- Added `CFUNCTIONS`

### windows.py
- Added `CFUNCTIONS`
- Added `MONITORNUMPROC`
- Removed `MSS.monitorenumproc`. Use `MONITORNUMPROC` instead.

## 6.0.0 (2020-06-30)

### base.py
- Added `lock`
- Added `MSS._grab_impl()` (abstract method)
- Added `MSS._monitors_impl()` (abstract method)
- `MSS.grab()` is no more an abstract method
- `MSS.monitors` is no more an abstract property

### darwin.py
- Renamed `MSS.grab()` to `MSS._grab_impl()`
- Renamed `MSS.monitors` to `MSS._monitors_impl()`

### linux.py
- Added `MSS.has_extension()`
- Removed `MSS.display`
- Renamed `MSS.grab()` to `MSS._grab_impl()`
- Renamed `MSS.monitors` to `MSS._monitors_impl()`

### windows.py
- Removed `MSS._lock`
- Renamed `MSS.srcdc_dict` to `MSS._srcdc_dict`
- Renamed `MSS.grab()` to `MSS._grab_impl()`
- Renamed `MSS.monitors` to `MSS._monitors_impl()`

## 5.1.0 (2020-04-30)

### base.py
- Renamed back `MSSMixin` class to `MSSBase`
- `MSSBase` is now derived from `abc.ABCMeta`
- `MSSBase.monitor` is now an abstract property
- `MSSBase.grab()` is now an abstract method

### windows.py
- Replaced `MSS.srcdc` with `MSS.srcdc_dict`

## 5.0.0 (2019-12-31)

### darwin.py
- Added `MSS.__slots__`

### linux.py
- Added `MSS.__slots__`
- Deleted `MSS.close()`
- Deleted `LAST_ERROR` constant. Use `ERROR` namespace instead, specially the `ERROR.details` attribute.

### models.py
- Added `Monitor`
- Added `Monitors`
- Added `Pixel`
- Added `Pixels`
- Added `Pos`
- Added `Size`

### screenshot.py
- Added `ScreenShot.__slots__`
- Removed `Pos`. Use `models.Pos` instead.
- Removed `Size`. Use `models.Size` instead.

### windows.py
- Added `MSS.__slots__`
- Deleted `MSS.close()`

## 4.0.1 (2019-01-26)

### linux.py
- Removed use of `MSS.xlib.XDefaultScreen()`
4.0.0 (2019-01-11)

### base.py
- Renamed `MSSBase` class to `MSSMixin`

### linux.py
- Renamed `MSS.__del__()` method to `MSS.close()`
- Deleted `MSS.last_error` attribute. Use `LAST_ERROR` constant instead.
- Added `validate()` function
- Added `MSS.get_error_details()` method

### windows.py
- Renamed `MSS.__exit__()` method to `MSS.close()`

## 3.3.0 (2018-09-04)

### exception.py
- Added `details` attribute to `ScreenShotError` exception. Empty dict by default.

### linux.py
- Added `error_handler()` function

## 3.2.1 (2018-05-21)

### windows.py
- Removed `MSS.scale_factor` property
- Removed `MSS.scale()` method

## 3.2.0 (2018-03-22)

### base.py
- Added `MSSBase.compression_level` attribute

### linux.py
- Added `MSS.drawable` attribute

### screenshot.py
- Added `Screenshot.bgra` attribute

### tools.py
- Changed signature of `to_png(data, size, output=None)` to `to_png(data, size, level=6, output=None)`. `level` is the Zlib compression level.

## 3.1.2 (2018-01-05)

### tools.py
- Changed signature of `to_png(data, size, output)` to `to_png(data, size, output=None)`. If `output` is `None`, the raw PNG bytes will be returned.

## 3.1.1 (2017-11-27)

### \_\_main\_\_.py
- Added `args` argument to `main()`

### base.py
- Moved `ScreenShot` class to `screenshot.py`

### darwin.py
- Added `CGPoint.__repr__()` function
- Added `CGRect.__repr__()` function
- Added `CGSize.__repr__()` function
- Removed `get_infinity()` function

### windows.py
- Added `MSS.scale()` method
- Added `MSS.scale_factor` property

## 3.0.0 (2017-07-06)

### base.py
- Added the `ScreenShot` class containing data for a given screen shot (support the Numpy array interface [`ScreenShot.__array_interface__`])
- Added `shot()` method to `MSSBase`. It takes the same arguments as the `save()` method.
- Renamed `get_pixels` to `grab`. It now returns a `ScreenShot` object.
- Moved `to_png` method to `tools.py`. It is now a simple function.
- Removed `enum_display_monitors()` method. Use `monitors` property instead.
- Removed `monitors` attribute. Use `monitors` property instead.
- Removed `width` attribute. Use `ScreenShot.size[0]` attribute or `ScreenShot.width` property instead.
- Removed `height` attribute. Use `ScreenShot.size[1]` attribute or `ScreenShot.height` property instead.
- Removed `image`. Use the `ScreenShot.raw` attribute or `ScreenShot.rgb` property instead.
- Removed `bgra_to_rgb()` method. Use `ScreenShot.rgb` property instead.

### darwin.py
- Removed `_crop_width()` method. Screen shots are now using the width set by the OS (rounded to 16).

### exception.py
- Renamed `ScreenshotError` class to `ScreenShotError`

### tools.py
- Changed signature of `to_png(data, monitor, output)` to `to_png(data, size, output)` where `size` is a `tuple(width, height)`
