"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import operator
import os
import shutil
from collections.abc import Callable, Generator
from functools import reduce
from hashlib import sha256
from pathlib import Path
from platform import system
from typing import Any
from zipfile import ZipFile

import pytest

from mss import MSS
from mss.linux import xcb, xlib


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--no-virtual-display",
        action="store_true",
        help="Do not run all the tests under Xvfb",
    )


@pytest.fixture(autouse=True)
def _no_warnings(recwarn: pytest.WarningsRecorder) -> Generator:
    """Fail on warning."""
    yield

    warnings = [f"{warning.filename}:{warning.lineno} {warning.message}" for warning in recwarn]
    for warning in warnings:
        print(warning)
    assert not warnings


_PURGE_GLOBS = {"*.png", "*.png.old"}


@pytest.fixture(scope="module", autouse=True)
def purge_files() -> Generator[None]:
    """Remove any .png or .png.old files created during the test module.

    This is useful for tests that generate screenshots, so that they
    don't accumulate in the source tree and pollute the results of
    future test runs.
    """
    before_images = reduce(operator.or_, (set(Path().glob(g)) for g in _PURGE_GLOBS))
    yield
    after_images = reduce(operator.or_, (set(Path().glob(g)) for g in _PURGE_GLOBS))
    new_images = after_images - before_images
    for file in new_images:
        print(f"Deleting {file} ...")
        file.unlink()


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


@pytest.fixture(params=["xlib", "xgetimage", "xshmgetimage"] if system() == "Linux" else ["default"])
def backend(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture
def mss_impl(backend: str) -> Callable[..., MSS]:
    # We can't just use partial here, since it will read $DISPLAY at the wrong time.  This can cause problems,
    # depending on just how the fixtures get run.
    def impl(*args: Any, **kwargs: Any) -> MSS:
        # I'm not really sure if adding an explicit display is needed anymore.  It was in a lot of existing code that
        # mss_impl replaced, but it should now be the default at this point.  I'll have to investigate.
        if system() == "Linux":
            kwargs = {"display": os.getenv("DISPLAY")} | kwargs
        return MSS(*args, backend=backend, **kwargs)

    return impl


@pytest.fixture(scope="session", autouse=True)
def virtual_display(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """Use Xvnc for the test session, if feasible.

    This isolates the testing from the development display.  This is
    necessary to test X backends under Wayland (XWayland doesn't allow
    programs to capture the root window), to avoid annoying the
    developer with transient windows during testing, and to avoid
    problems with the screen changing during tests that expect
    successive screenshots to be identical.

    If Xvfb and pyvirtualdisplay are not available, then the current
    display is used as a fallback.
    """
    if system() != "Linux" or request.config.getoption("--no-virtual-display") or shutil.which("Xvfb") is None:
        yield
        return

    try:
        from pyvirtualdisplay import Display  # noqa: PLC0415
    except ImportError:
        yield
        return

    # We use 1280x1024 since test_issue_220 requires it.  The default for pyvirtualdisplay is manage_global_env=True,
    # but we make it explicit here to forestall future changes.  We use MonkeyPatch to make sure that nothing tries to
    # use Wayland, which would bypass $DISPLAY.
    with Display(size=(1280, 1024), manage_global_env=True), pytest.MonkeyPatch.context() as mp:
        mp.delenv("WAYLAND_DISPLAY", raising=False)
        mp.delenv("XDG_SESSION_TYPE", raising=False)
        yield


@pytest.fixture(scope="session", autouse=True)
def inhibit_x11_resets(virtual_display: None) -> Generator[None, None, None]:  # noqa: ARG001 virtual_display is for ordering
    """Ensure that an X11 connection is open during the test session.

    Under X11, when the last client disconnects, the server resets.  If
    a new client tries to connect before the reset is complete, it may fail.
    Since we often run the tests under Xvfb, they're frequently the only
    clients.  Since our tests run in rapid succession, this combination
    can lead to intermittent failures.

    To avoid this, we open a connection at the start of the test session
    and keep it open until the end.
    """
    if system() != "Linux":
        yield
        return

    conn, _ = xcb.connect()
    try:
        yield
    finally:
        # Some tests may have reset xcb.LIB, so make sure it's currently initialized.
        xcb.initialize()
        xcb.disconnect(conn)
