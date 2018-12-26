# coding: utf-8
import os
import platform

from mss import mss

import pytest


OS = platform.system().lower()
PID = os.getpid()


def get_opened_socket():
    # type: () -> int
    """
    GNU/Linux: a way to get the opened sockets count.
    It will be used to check X server connections are well closed.
    """

    import subprocess

    cmd = "lsof -U | grep {}".format(PID)
    output = subprocess.check_output(cmd, shell=True)
    return len(output.splitlines())


def get_handles():
    # type: () -> int
    """
    Windows: a way to get the GDI handles count.
    It will be used to check the handles count is not growing, showing resource leaks.
    """

    import ctypes

    PQI = 0x400  # PROCESS_QUERY_INFORMATION
    GR_GDIOBJECTS = 0
    h = ctypes.windll.kernel32.OpenProcess(PQI, 0, PID)
    return ctypes.windll.user32.GetGuiResources(h, GR_GDIOBJECTS)


@pytest.fixture
def monitor_func():
    # type: () -> Callable
    """ OS specific function to check resources in use. """

    if OS == "linux":
        return get_opened_socket
    elif OS == "windows":
        return get_handles


def bound_instance_without_cm():
    """ This is bad. """
    sct = mss()
    sct.shot()


def bound_instance_without_cm_but_use_close():
    """ This is better. """
    sct = mss()
    sct.shot()
    sct.close()
    # Calling .close() twice should be possible
    sct.close()


def unbound_instance_without_cm():
    """ This is really bad. """
    mss().shot()


def with_context_manager():
    """ This is the best. """
    with mss() as sct:
        sct.shot()


@pytest.mark.skipif(OS == "darwin", reason="No possible leak on macOS.")
@pytest.mark.parametrize(
    "func, will_leak_resources",
    (
        (bound_instance_without_cm, True),
        (bound_instance_without_cm_but_use_close, False),
        (unbound_instance_without_cm, True),
        (with_context_manager, False),
    ),
)
def test_resource_leaks(func, will_leak_resources, monitor_func):
    """ Check for resource leaks with different use cases. """

    original_resources = monitor_func()
    allocated_resources = 0

    for _ in range(5):
        func()
        new_resources = monitor_func()
        allocated_resources = max(allocated_resources, new_resources)

    if will_leak_resources:
        assert original_resources < allocated_resources
        pytest.xfail("Resources leak!")
    else:
        assert original_resources == allocated_resources
