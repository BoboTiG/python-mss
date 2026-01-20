# History

See Git checking messages for full history.

## 10.2.0.dev0 (2025-xx-xx)
- Linux: check the server for Xrandr support version (#417)
- Linux: improve typing and error messages for X libraries (#418)
- Linux: introduce an XCB-powered backend stack with a factory in ``mss.linux`` while keeping the Xlib code as a fallback (#425)
- Linux: add the XShmGetImage backend with automatic XGetImage fallback and explicit status reporting (#431)
- Windows: improve error checking and messages for Win32 API calls (#448)
- Mac: fix memory leak (#450, #453)
- improve multithreading: allow multiple threads to use the same MSS object, allow multiple MSS objects to concurrently take screenshots, and document multithreading guarantees (#446, #452)
- Add full demos for different ways to use MSS (#444, #456)
- :heart: contributors: @jholveck

## 10.1.0 (2025-08-16)
- Mac: up to 60% performances improvement by taking screenshots at nominal resolution (e.g. scaling is off by default). To enable back scaling, set `mss.darwin.IMAGE_OPTIONS = 0`. (#257)
- docs: use the [shibuya](https://shibuya.lepture.com) theme
- :heart: contributors: @brycedrennan

## 10.0.0 (2024-11-14)
- removed support for Python 3.8
- added support for Python 3.14
- Linux: fixed a threading issue in `.close()` when calling `XCloseDisplay()` (#251)
- Linux: minor optimization when checking for a X extension status (#251)
- :heart: contributors: @kianmeng, @shravanasati, @mgorny

## 9.0.2 (2024-09-01)
- added support for Python 3.13
- leveled up the packaging using `hatchling`
- used `ruff` to lint the code base (#275)
- MSS: minor optimization when using an output file format without date (#275)
- MSS: fixed `Pixel` model type (#274)
- CI: automated release publishing on tag creation
- :heart: contributors: @Andon-Li

## 9.0.1 (2023-04-20)
- CLI: fixed entry point not taking into account arguments

## 9.0.0 (2023-04-18)
- Linux: add failure handling to `XOpenDisplay()` call (fixes #246)
- Mac: tiny improvement in monitors finding
- Windows: refactored how internal handles are stored (fixes #198)
- Windows: removed side effects when leaving the context manager, resources are all freed (fixes #209)
- CI: run tests via `xvfb-run` on GitHub Actions (#248)
- tests: enhance `test_get_pixels.py`, and try to fix a random failure at the same time (related to #251)
- tests: use `PyVirtualDisplay` instead of `xvfbwrapper` (#249)
- tests: automatic rerun in case of failure (related to #251)
- :heart: contributors: @mgorny, @CTPaHHuK-HEbA

## 8.0.3 (2023-04-15)
- added support for Python 3.12
- MSS: added PEP 561 compatibility
- MSS: include more files in the sdist package (#240)
- Linux: restore the original X error handler in `.close()` (#241)
- Linux: fixed `XRRCrtcInfo.width`, and `XRRCrtcInfo.height`, C types
- docs: use Markdown for the README, and changelogs
- dev: renamed the `master` branch to `main`
- dev: review the structure of the repository to fix/improve packaging issues (#243)
- :heart: contributors: @mgorny, @relent95

## 8.0.2 (2023-04-09)
- fixed `SetuptoolsDeprecationWarning`: Installing 'XXX' as data is deprecated, please list it in packages
- CLI: fixed arguments handling

## 8.0.1 (2023-04-09)
- MSS: ensure `--with-cursor`, and `with_cursor` argument & attribute, are simple NOOP on platforms not supporting the feature
- CLI: do not raise a `ScreenShotError` when `-q`, or `--quiet`, is used but return `
- tests: fixed `test_entry_point()` with multiple monitors having the same resolution

## 8.0.0 (2023-04-09)
- removed support for Python 3.6
- removed support for Python 3.7
- MSS: fixed PEP 484 prohibits implicit Optional
- MSS: the whole source code was migrated to PEP 570 (Python positional-only parameters)
- Linux: reset the X server error handler on exit to prevent issues with Tk/Tkinter (fixes #220)
- Linux: refactored how internal handles are stored to fixed issues with multiple X servers (fixes #210)
- Linux: removed side effects when leaving the context manager, resources are all freed (fixes #210)
- Linux: added mouse support (related to #55)
- CLI: added `--with-cursor` argument
- tests: added PyPy 3.9, removed `tox`, and improved GNU/Linux coverage
- :heart: contributors: @zorvios

## 7.0.1 (2022-10-27)
- fixed the wheel package

## 7.0.0 (2022-10-27)
- added support for Python 3.11
- added support for Python 3.10
- removed support for Python 3.5
- MSS: modernized the code base (types, `f-string`, ran `isort` & `black`) (closes #101)
- MSS: fixed several Sourcery issues
- MSS: fixed typos here, and there
- docs: fixed an error when building the documentation

## 6.1.0 (2020-10-31)
- MSS: reworked how C functions are initialized
- Mac: reduce the number of function calls
- Mac: support macOS Big Sur (fixes #178)
- tests: expand Python versions to 3.9 and 3.10
- tests: fixed macOS interpreter not found on Travis-CI
- tests: fixed `test_entry_point()` when there are several monitors

## 6.0.0 (2020-06-30)
- removed usage of deprecated `license_file` option for `license_files`
- fixed flake8 usage in pre-commit
- the module is now available on Conda (closes #170)
- MSS: the implementation is now thread-safe on all OSes (fixes #169)
- Linux: better handling of the Xrandr extension (fixes #168)
- tests: fixed a random bug on `test_grab_with_tuple_percents()` (fixes #142)

## 5.1.0 (2020-04-30)
- produce wheels for Python 3 only
- MSS: renamed again `MSSMixin` to `MSSBase`, now derived from `abc.ABCMeta`
- tools: force write of file when saving a PNG file
- tests: fixed tests on macOS with Retina display
- Windows: fixed multi-thread safety (fixes #150)
- :heart: contributors: @narumishi

## 5.0.0 (2019-12-31)
- removed support for Python 2.7
- MSS: improve type annotations and add CI check
- MSS: use `__slots__` for better performances
- MSS: better handle resources to prevent leaks
- MSS: improve monitors finding
- Windows: use our own instances of `GDI32` and `User32` DLLs
- docs: add `project_urls` to `setup.cfg`
- docs: add an example using the multiprocessing module (closes #82)
- tests: added regression tests for #128 and #135
- tests: move tests files into the package
- :heart: contributors: @hugovk, @foone, @SergeyKalutsky

## 4.0.2 (2019-02-23)
- Windows: ignore missing `SetProcessDPIAware()` on Window XP (fixes #109)
- :heart: contributors: @foone

## 4.0.1 (2019-01-26)
- Linux: fixed several Xlib functions signature (fixes #92)
- Linux: improve monitors finding by a factor of 44

## 4.0.0 (2019-01-11)
- MSS: remove use of `setup.py` for `setup.cfg`
- MSS: renamed `MSSBase` to `MSSMixin` in `base.py`
- MSS: refactor ctypes `argtype`, `restype` and `errcheck` setup (fixes #84)
- Linux: ensure resources are freed in `grab()`
- Windows: avoid unnecessary class attributes
- MSS: ensure calls without context manager will not leak resources or document them (fixes #72 and #85)
- MSS: fixed Flake8 C408: Unnecessary dict call - rewrite as a literal, in `exceptions.py`
- MSS: fixed Flake8 I100: Import statements are in the wrong order
- MSS: fixed Flake8 I201: Missing newline before sections or imports
- MSS: fixed PyLint bad-super-call: Bad first argument 'Exception' given to `super()`
- tests: use `tox`, enable PyPy and PyPy3, add macOS and Windows CI

## 3.3.2 (2018-11-20)
- MSS: do monitor detection in MSS constructor (fixes #79)
- MSS: specify compliant Python versions for pip install
- tests: enable Python 3.7
- tests: fixed `test_entry_point()` with multiple monitors
- :heart: contributors: @hugovk, @andreasbuhr

## 3.3.1 (2018-09-22)
- Linux: fixed a memory leak introduced with 7e8ae5703f0669f40532c2be917df4328bc3985e (fixes #72)
- docs: add the download statistics badge

## 3.3.0 (2018-09-04)
- Linux: add an error handler for the XServer to prevent interpreter crash (fixes #61)
- MSS: fixed a `ResourceWarning`: unclosed file in `setup.py`
- tests: fixed a `ResourceWarning`: unclosed file
- docs: fixed a typo in `Screenshot.pixel()` method (thanks to @mchlnix)
- big code clean-up using `black`

## 3.2.1 (2018-05-21)
- Windows: enable Hi-DPI awareness
- :heart: contributors: @ryanfox

## 3.2.0 (2018-03-22)
- removed support for Python 3.4
- MSS: add the `Screenshot.bgra` attribute
- MSS: speed-up grabbing on the 3 platforms
- tools: add PNG compression level control to `to_png()`
- tests: add `leaks.py` and `benchmarks.py` for manual testing
- docs: add an example about capturing part of the monitor 2
- docs: add an example about computing BGRA values to RGB

## 3.1.2 (2018-01-05)
- removed support for Python 3.3
- MSS: possibility to get the whole PNG raw bytes
- Windows: capture all visible window
- docs: improvements and fixes (fixes #37)
- CI: build the documentation

## 3.1.1 (2017-11-27)
- MSS: add the `mss` entry point

## 3.1.0 (2017-11-16)
- MSS: add more way of customization to the output argument of `save()`
- MSS: possibility to use custom class to handle screenshot data
- Mac: properly support all display scaling and resolutions (fixes #14, #19, #21, #23)
- Mac: fixed memory leaks (fixes #24)
- Linux: handle bad display value
- Windows: take into account zoom factor for high-DPI displays (fixes #20)
- docs: several fixes (fixes #22)
- tests: a lot of tests added for better coverage
- add the 'Say Thanks' button
- :heart: contributors: @karanlyons

## 3.0.1 (2017-07-06)
- fixed examples links

## 3.0.0 (2017-07-06)
- big refactor, introducing the `ScreenShot` class
- MSS: add Numpy array interface support to the `Screenshot` class
- docs: add OpenCV/Numpy, PIL pixels, FPS

## 2.0.22 (2017-04-29)
- MSS: better use of exception mechanism
- Linux: use of `hasattr()` to prevent Exception on early exit
- Mac: take into account extra black pixels added when screen with is not divisible by 16 (fixes #14)
- docs: add an example to capture only a part of the screen
- :heart: contributors: David Becker, @redodo

## 2.0.18 (2016-12-03)
- change license to MIT
- MSS: add type hints
- MSS: remove unused code (reported by `Vulture`)
- Linux: remove MSS library
- Linux: insanely fast using only ctypes
- Linux: skip unused monitors
- Linux: use `errcheck` instead of deprecated `restype` with callable (fixes #11)
- Linux: fixed security issue (reported by Bandit)
- docs: add documentation (fixes #10)
- tests: add tests and use Travis CI (fixes #9)
- :heart: contributors: @cycomanic

## 2.0.0 (2016-06-04)
- add issue and pull request templates
- split the module into several files
- MSS: a lot of code refactor and optimizations
- MSS: rename `save_img()` to `to_png()`
- MSS: `save()`: replace `screen` argument by `mon`
- Mac: get rid of the `PyObjC` module, 100% ctypes
- Linux: prevent segfault when `DISPLAY` is set but no X server started
- Linux: prevent segfault when Xrandr is not loaded
- Linux: `get_pixels()` insanely fast, use of MSS library (C code)
- Windows: screenshot not correct on Windows 8 (fixes #6)

## 1.0.2 (2016-04-22)
- MSS: fixed non-existent alias

## 1.0.1 (2016-04-22)
- MSS: `libpng` warning (ignoring bad filter type) (fixes #7)

## 1.0.0 (2015-04-16)
- Python 2.6 to 3.5 ready
- MSS: code clean-up and review, no more debug information
- MSS: add a shortcut to take automatically use the proper `MSS` class (fixes #5)
- MSS: few optimizations into `save_img()`
- Darwin: remove rotation from information returned by `enum_display_monitors()`
- Linux: fixed `object has no attribute 'display' into __del__`
- Linux: use of `XDestroyImage()` instead of `XFree()`
- Linux: optimizations of `get_pixels()`
- Windows: huge optimization of `get_pixels()`
- CLI: delete `--debug` argument

## 0.1.1 (2015-04-10)
- MSS: little code review
- Linux: fixed monitor count
- tests: remove `test-linux` binary
- docs: add `doc/TESTING`
- docs: remove Bonus section from README

## 0.1.0 (2015-04-10)
- MSS: fixed code with `YAPF` tool
- Linux: fully functional using Xrandr library
- Linux: code clean-up (no more XML files to parse)
- docs: better tests and examples

## 0.0.8 (2015-02-04)
- MSS: filename's directory is not used when saving (fixes #3)
- MSS: fixed flake8 error: E713 test for membership should be 'not in'
- MSS: raise an exception for unimplemented methods
- Windows: robustness to `MSSWindows.get_pixels` (fixes #4)
- :heart: contributors: @sergey-vin, @thehesiod

## 0.0.7 (2014-03-20)
- MSS: fixed path where screenshots are saved

## 0.0.6 (2014-03-19)
- Python 3.4 ready
- PEP8 compliant
- MSS: review module structure to fit the "Code Like a Pythonista: Idiomatic Python"
- MSS: refactoring of all `enum_display_monitors()` methods
- MSS: fixed misspellings using `codespell` tool
- MSS: better way to manage output filenames (callback)
- MSS: several fixes here and there, code refactoring
- Linux: add XFCE4 support
- CLI: possibility to append `--debug` to the command line
- :heart: contributors: @sametmax

## 0.0.5 (2013-11-01)
- MSS: code simplified
- Windows: few optimizations into `_arrange()`

## 0.0.4 (2013-10-31)
- Linux: use of memoization → huge time/operations gains

## 0.0.3 (2013-10-30)
- MSS: removed PNG filters
- MSS: removed `ext` argument, using only PNG
- MSS: do not overwrite existing image files
- MSS: few optimizations into `png()`
- Linux: few optimizations into `get_pixels()`

## 0.0.2 (2013-10-21)
- added support for python 3 on Windows and GNU/Linux
- :heart: contributors: Oros, Eownis

## 0.0.1 (2013-07-01)
- first release
