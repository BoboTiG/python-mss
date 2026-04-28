"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import mss
import mss.base


def test_top_level_export_surface_exists() -> None:
    assert hasattr(mss, "mss")  # TODO(jholveck): #517 Remove compatibility path once 10.x transition period ends.
    assert hasattr(mss, "MSS")
    assert hasattr(mss, "ScreenShotError")
    assert hasattr(mss, "__version__")
