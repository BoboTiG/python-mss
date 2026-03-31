"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform
import warnings
from collections.abc import Callable
from os import getenv
from typing import Protocol, cast

import pytest

import mss
from mss import MSS
from mss.base import MSSBase


class PlatformModule(Protocol):
    MSS: type[MSS]


MSSFactory = Callable[[], MSS]
MSSFactoryGetter = Callable[[], MSSFactory]


def _factory_from_import_style() -> MSSFactory:
    from mss import mss as mss_factory  # noqa: PLC0415

    return cast("MSSFactory", mss_factory)


def _factory_from_module_style() -> MSSFactory:
    import mss as mss_module  # noqa: PLC0415

    return mss_module.mss


def _platform_module() -> PlatformModule:
    os_ = platform.system().lower()

    if os_ == "linux":
        import mss.linux as mss_platform  # noqa: PLC0415

        return cast("PlatformModule", mss_platform)
    if os_ == "darwin":
        import mss.darwin as mss_platform  # type: ignore[no-redef] # noqa: PLC0415

        return cast("PlatformModule", mss_platform)
    if os_ == "windows":
        import mss.windows as mss_platform  # type: ignore[no-redef] # noqa: PLC0415

        return cast("PlatformModule", mss_platform)
    msg = f"Unsupported platform for compatibility test: {os_!r}"
    raise AssertionError(msg)


def _platform_factory_from_import_style() -> type[MSS]:
    os_ = platform.system().lower()

    if os_ == "linux":
        import mss.linux  # noqa: PLC0415

        return mss.linux.MSS
    if os_ == "darwin":
        import mss.darwin  # noqa: PLC0415

        return mss.darwin.MSS
    if os_ == "windows":
        import mss.windows  # noqa: PLC0415

        return mss.windows.MSS
    msg = f"Unsupported platform for compatibility test: {os_!r}"
    raise AssertionError(msg)


@pytest.mark.parametrize(
    "factory_getter",
    [
        lambda: mss.mss,
        _factory_from_import_style,
        _factory_from_module_style,
    ],
)
def test_mss_factory_documented_styles_return_mssbase(factory_getter: MSSFactoryGetter) -> None:
    factory = factory_getter()

    with pytest.warns(DeprecationWarning, match=r"^mss\.mss is deprecated"):
        context = factory()

    with context as sct:
        assert isinstance(sct, MSSBase)
        assert isinstance(sct, MSS)


def test_documented_style_platform_import_mss() -> None:
    mss_factory = _platform_factory_from_import_style()

    with pytest.warns(DeprecationWarning, match=r"^mss\..*\.MSS is deprecated"):
        context = mss_factory()

    with context as sct:
        assert isinstance(sct, MSSBase)


def test_direct_mss_constructor_has_no_deprecation_warning() -> None:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", DeprecationWarning)
        with mss.MSS() as sct:
            assert isinstance(sct, MSS)
    assert not [warning for warning in captured if issubclass(warning.category, DeprecationWarning)]


def test_mssbase_alias_stays_compatible() -> None:
    # 10.1-compatible typing/import path.
    assert MSSBase is MSS


def test_platform_mss_constructor_works_on_current_platform() -> None:
    mss_platform = _platform_module()

    with pytest.warns(DeprecationWarning, match=r"^mss\..*\.MSS is deprecated"):
        sct_context = mss_platform.MSS()

    with sct_context as sct:
        assert isinstance(sct, mss_platform.MSS)
        assert isinstance(sct, MSSBase)
        assert isinstance(sct, MSS)


def test_factory_and_platform_constructor_are_compatible_types() -> None:
    mss_platform = _platform_module()

    with pytest.warns(DeprecationWarning, match=r"^mss\..*\.MSS is deprecated"):
        from_platform_context = mss_platform.MSS()

    with pytest.warns(DeprecationWarning, match=r"^mss\.mss is deprecated"):
        from_factory_context = mss.mss()

    with from_factory_context as from_factory, from_platform_context as from_platform:
        assert type(from_factory) is MSS
        assert type(from_platform) is mss_platform.MSS
        assert isinstance(from_platform, MSS)
        assert isinstance(from_platform, MSSBase)


def test_deprecated_factory_accepts_documented_kwargs() -> None:
    """Verify that kwargs are accepted, even if not relevant.

    All 10.1-documented kwargs were accepted on every platform, even
    if only meaningful on one.  Verify that still works via the
    deprecated factory.
    """
    kwargs = {
        "compression_level": 1,
        "with_cursor": True,
        "max_displays": 1,
        "display": getenv("DISPLAY"),  # None on non-Linux
    }

    with (
        pytest.warns(DeprecationWarning, match=r"^mss\.mss is deprecated"),
        pytest.warns(DeprecationWarning, match=r"is only available on"),
    ):
        context = mss.mss(**kwargs)

    with context as sct:
        assert isinstance(sct, MSSBase)
