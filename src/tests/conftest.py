"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os
from collections.abc import Callable, Generator
from hashlib import sha256
from pathlib import Path
from platform import system
from zipfile import ZipFile

import pytest

from mss import mss
from mss.base import MSSBase
from mss.linux import xcb, xlib


@pytest.fixture(autouse=True)
def _no_warnings(recwarn: pytest.WarningsRecorder) -> Generator:
    """Fail on warning."""
    yield

    warnings = [f"{warning.filename}:{warning.lineno} {warning.message}" for warning in recwarn]
    for warning in warnings:
        print(warning)
    assert not warnings


def purge_files() -> None:
    """Remove all generated files from previous runs."""
    for file in Path().glob("*.png"):
        print(f"Deleting {file} ...")
        file.unlink()

    for file in Path().glob("*.png.old"):
        print(f"Deleting {file} ...")
        file.unlink()


@pytest.fixture(scope="module", autouse=True)
def _before_tests() -> None:
    purge_files()


@pytest.fixture(autouse=True)
def no_xlib_errors(request: pytest.FixtureRequest) -> None:
    system() == "Linux" and ("backend" not in request.fixturenames or request.getfixturevalue("backend") == "xlib")
    assert not xlib._ERROR


@pytest.fixture(autouse=True)
def reset_xcb_libraries(request: pytest.FixtureRequest) -> Generator[None]:
    # We need to test this before we yield, since the backend isn't available afterwards.
    xcb_should_reset = system() == "Linux" and (
        "backend" not in request.fixturenames or request.getfixturevalue("backend") == "xcb"
    )
    yield None
    if xcb_should_reset:
        xcb.LIB.reset()


@pytest.fixture(scope="session")
def raw() -> bytes:
    file = Path(__file__).parent / "res" / "monitor-1024x768.raw.zip"
    with ZipFile(file) as fh:
        data = fh.read(file.with_suffix("").name)

    assert sha256(data).hexdigest() == "d86ed4366d5a882cfe1345de82c87b81aef9f9bf085f4c42acb6f63f3967eccd"
    return data


@pytest.fixture(params=["xlib", "xgetimage"] if system() == "Linux" else ["default"])
def backend(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def mss_impl(backend: str) -> Callable[..., MSSBase]:
    # We can't just use partial here, since it will read $DISPLAY at the wrong time.  This can cause problems,
    # depending on just how the fixtures get run.
    return lambda *args, **kwargs: mss(*args, display=os.getenv("DISPLAY"), backend=backend, **kwargs)
