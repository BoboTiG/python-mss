"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import ctypes
import os
import platform
import subprocess
from collections.abc import Callable

import pytest

import mss

OS = platform.system().lower()
PID = os.getpid()


def get_opened_socket() -> int:
    """GNU/Linux: a way to get the opened sockets count.
    It will be used to check X server connections are well closed.
    """
    cmd = f"lsof -U | grep {PID}"
    output = subprocess.check_output(cmd, shell=True)
    return len(output.splitlines())


def get_handles() -> int:
    """Windows: a way to get the GDI handles count.
    It will be used to check the handles count is not growing, showing resource leaks.
    """
    PROCESS_QUERY_INFORMATION = 0x400  # noqa:N806
    GR_GDIOBJECTS = 0  # noqa:N806
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, 0, PID)
    return ctypes.windll.user32.GetGuiResources(h, GR_GDIOBJECTS)


@pytest.fixture
def monitor_func() -> Callable[[], int]:
    """OS specific function to check resources in use."""
    return get_opened_socket if OS == "linux" else get_handles


def bound_instance_without_cm() -> None:
    # Will always leak
    sct = mss.mss()
    sct.shot()


def bound_instance_without_cm_but_use_close() -> None:
    sct = mss.mss()
    sct.shot()
    sct.close()
    # Calling .close() twice should be possible
    sct.close()


def unbound_instance_without_cm() -> None:
    # Will always leak
    mss.mss().shot()


def with_context_manager() -> None:
    with mss.mss() as sct:
        sct.shot()


def regression_issue_128() -> None:
    """Regression test for issue #128: areas overlap."""
    with mss.mss() as sct:
        area1 = {"top": 50, "left": 7, "width": 400, "height": 320, "mon": 1}
        sct.grab(area1)
        area2 = {"top": 200, "left": 200, "width": 320, "height": 320, "mon": 1}
        sct.grab(area2)


def regression_issue_135() -> None:
    """Regression test for issue #135: multiple areas."""
    with mss.mss() as sct:
        bounding_box_notes = {"top": 0, "left": 0, "width": 100, "height": 100}
        sct.grab(bounding_box_notes)
        bounding_box_test = {"top": 220, "left": 220, "width": 100, "height": 100}
        sct.grab(bounding_box_test)
        bounding_box_score = {"top": 110, "left": 110, "width": 100, "height": 100}
        sct.grab(bounding_box_score)


def regression_issue_210() -> None:
    """Regression test for issue #210: multiple X servers."""
    pyvirtualdisplay = pytest.importorskip("pyvirtualdisplay")

    with pyvirtualdisplay.Display(size=(1920, 1080), color_depth=24), mss.mss():
        pass

    with pyvirtualdisplay.Display(size=(1920, 1080), color_depth=24), mss.mss():
        pass


@pytest.mark.skipif(OS == "darwin", reason="No possible leak on macOS.")
@pytest.mark.parametrize(
    "func",
    [
        # bound_instance_without_cm,
        bound_instance_without_cm_but_use_close,
        # unbound_instance_without_cm,
        with_context_manager,
        regression_issue_128,
        regression_issue_135,
        regression_issue_210,
    ],
)
def test_resource_leaks(func: Callable[[], None], monitor_func: Callable[[], int]) -> None:
    """Check for resource leaks with different use cases."""
    # Warm-up
    func()

    original_resources = monitor_func()
    allocated_resources = 0

    for _ in range(5):
        func()
        new_resources = monitor_func()
        allocated_resources = max(allocated_resources, new_resources)

    assert allocated_resources <= original_resources
