"""An ultra fast cross-platform multiple screenshots module in pure python
using ctypes.

This module is maintained by Mickaël Schoentgen <contact@tiger-222.fr>.

You can always get the latest version of this module at:
    https://github.com/BoboTiG/python-mss
If that URL should fail, try contacting the author.
"""

from mss.exception import ScreenShotError
from mss.factory import mss

__version__ = "10.0.0"
__author__ = "Mickaël Schoentgen"
__date__ = "2013-2024"
__copyright__ = f"""
Copyright (c) {__date__}, {__author__}

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose and without fee or royalty is hereby
granted, provided that the above copyright notice appear in all copies
and that both that copyright notice and this permission notice appear
in supporting documentation or portions thereof, including
modifications, that you make.
"""
__all__ = ("ScreenShotError", "mss")
