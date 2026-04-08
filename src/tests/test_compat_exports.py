"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import mss
import mss.base


def test_top_level_export_surface_exists() -> None:
    # TODO(jholveck): #493 Remove compatibility-only export checks after 10.x transition period.
    assert hasattr(mss, "mss")
    assert hasattr(mss, "MSS")
    assert hasattr(mss, "ScreenShotError")
    assert hasattr(mss, "__version__")


def test_mssbase_compat_symbol_exists() -> None:
    # TODO(jholveck): #493 Remove compatibility-only export checks after 10.x transition period.
    assert hasattr(mss.base, "MSSBase")
