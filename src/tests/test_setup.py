"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import platform
import tarfile
from subprocess import STDOUT, check_call, check_output
from zipfile import ZipFile

import pytest

from mss import __version__

if platform.system().lower() != "linux":
    pytestmark = pytest.mark.skip

pytest.importorskip("build")
pytest.importorskip("twine")

SDIST = ["python", "-m", "build", "--sdist"]
WHEEL = ["python", "-m", "build", "--wheel"]
CHECK = ["twine", "check", "--strict"]


def test_sdist() -> None:
    output = check_output(SDIST, stderr=STDOUT, text=True)
    file = f"mss-{__version__}.tar.gz"
    assert f"Successfully built {file}" in output
    assert "warning" not in output.lower()

    check_call([*CHECK, f"dist/{file}"])

    with tarfile.open(f"dist/{file}", mode="r:gz") as fh:
        files = sorted(fh.getnames())

    assert files == [
        f"mss-{__version__}/.gitignore",
        f"mss-{__version__}/CHANGELOG.md",
        f"mss-{__version__}/CHANGES.md",
        f"mss-{__version__}/CONTRIBUTORS.md",
        f"mss-{__version__}/LICENSE.txt",
        f"mss-{__version__}/PKG-INFO",
        f"mss-{__version__}/README.md",
        f"mss-{__version__}/docs/source/api.rst",
        f"mss-{__version__}/docs/source/conf.py",
        f"mss-{__version__}/docs/source/developers.rst",
        f"mss-{__version__}/docs/source/examples.rst",
        f"mss-{__version__}/docs/source/examples/callback.py",
        f"mss-{__version__}/docs/source/examples/custom_cls_image.py",
        f"mss-{__version__}/docs/source/examples/fps.py",
        f"mss-{__version__}/docs/source/examples/fps_multiprocessing.py",
        f"mss-{__version__}/docs/source/examples/from_pil_tuple.py",
        f"mss-{__version__}/docs/source/examples/linux_display_keyword.py",
        f"mss-{__version__}/docs/source/examples/opencv_numpy.py",
        f"mss-{__version__}/docs/source/examples/part_of_screen.py",
        f"mss-{__version__}/docs/source/examples/part_of_screen_monitor_2.py",
        f"mss-{__version__}/docs/source/examples/pil.py",
        f"mss-{__version__}/docs/source/examples/pil_pixels.py",
        f"mss-{__version__}/docs/source/index.rst",
        f"mss-{__version__}/docs/source/installation.rst",
        f"mss-{__version__}/docs/source/support.rst",
        f"mss-{__version__}/docs/source/usage.rst",
        f"mss-{__version__}/docs/source/where.rst",
        f"mss-{__version__}/pyproject.toml",
        f"mss-{__version__}/src/mss/__init__.py",
        f"mss-{__version__}/src/mss/__main__.py",
        f"mss-{__version__}/src/mss/base.py",
        f"mss-{__version__}/src/mss/darwin.py",
        f"mss-{__version__}/src/mss/exception.py",
        f"mss-{__version__}/src/mss/factory.py",
        f"mss-{__version__}/src/mss/linux.py",
        f"mss-{__version__}/src/mss/models.py",
        f"mss-{__version__}/src/mss/py.typed",
        f"mss-{__version__}/src/mss/screenshot.py",
        f"mss-{__version__}/src/mss/tools.py",
        f"mss-{__version__}/src/mss/windows.py",
        f"mss-{__version__}/src/tests/__init__.py",
        f"mss-{__version__}/src/tests/bench_bgra2rgb.py",
        f"mss-{__version__}/src/tests/bench_general.py",
        f"mss-{__version__}/src/tests/conftest.py",
        f"mss-{__version__}/src/tests/res/monitor-1024x768.raw.zip",
        f"mss-{__version__}/src/tests/test_bgra_to_rgb.py",
        f"mss-{__version__}/src/tests/test_cls_image.py",
        f"mss-{__version__}/src/tests/test_find_monitors.py",
        f"mss-{__version__}/src/tests/test_get_pixels.py",
        f"mss-{__version__}/src/tests/test_gnu_linux.py",
        f"mss-{__version__}/src/tests/test_implementation.py",
        f"mss-{__version__}/src/tests/test_issue_220.py",
        f"mss-{__version__}/src/tests/test_leaks.py",
        f"mss-{__version__}/src/tests/test_macos.py",
        f"mss-{__version__}/src/tests/test_save.py",
        f"mss-{__version__}/src/tests/test_setup.py",
        f"mss-{__version__}/src/tests/test_tools.py",
        f"mss-{__version__}/src/tests/test_windows.py",
        f"mss-{__version__}/src/tests/third_party/__init__.py",
        f"mss-{__version__}/src/tests/third_party/test_numpy.py",
        f"mss-{__version__}/src/tests/third_party/test_pil.py",
    ]


def test_wheel() -> None:
    output = check_output(WHEEL, stderr=STDOUT, text=True)
    file = f"mss-{__version__}-py3-none-any.whl"
    assert f"Successfully built {file}" in output
    assert "warning" not in output.lower()

    check_call([*CHECK, f"dist/{file}"])

    with ZipFile(f"dist/{file}") as fh:
        files = sorted(fh.namelist())

    assert files == [
        f"mss-{__version__}.dist-info/METADATA",
        f"mss-{__version__}.dist-info/RECORD",
        f"mss-{__version__}.dist-info/WHEEL",
        f"mss-{__version__}.dist-info/entry_points.txt",
        f"mss-{__version__}.dist-info/licenses/LICENSE.txt",
        "mss/__init__.py",
        "mss/__main__.py",
        "mss/base.py",
        "mss/darwin.py",
        "mss/exception.py",
        "mss/factory.py",
        "mss/linux.py",
        "mss/models.py",
        "mss/py.typed",
        "mss/screenshot.py",
        "mss/tools.py",
        "mss/windows.py",
    ]
