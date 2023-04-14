"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
import platform
from subprocess import STDOUT, check_call, check_output

import pytest

from mss import __version__

if platform.system().lower() != "linux":
    pytestmark = pytest.mark.skip

pytest.importorskip("build")
pytest.importorskip("twine")

SDIST = "python -m build --sdist".split()
WHEEL = "python -m build --wheel".split()
CHECK = "twine check dist/*".split()


def test_sdist():
    output = check_output(SDIST, stderr=STDOUT, text=True)
    expected = f"""
creating mss-{__version__}
creating mss-{__version__}/docs
creating mss-{__version__}/docs/source
creating mss-{__version__}/docs/source/examples
creating mss-{__version__}/src
creating mss-{__version__}/src/mss
creating mss-{__version__}/src/mss.egg-info
creating mss-{__version__}/src/tests
creating mss-{__version__}/src/tests/res
copying files to mss-{__version__}...
copying CHANGELOG.md -> mss-{__version__}
copying CHANGES.md -> mss-{__version__}
copying CONTRIBUTORS.md -> mss-{__version__}
copying LICENSE.txt -> mss-{__version__}
copying MANIFEST.in -> mss-{__version__}
copying README.md -> mss-{__version__}
copying dev-requirements.txt -> mss-{__version__}
copying setup.cfg -> mss-{__version__}
copying setup.py -> mss-{__version__}
copying tests-requirements.txt -> mss-{__version__}
copying docs/source/api.rst -> mss-{__version__}/docs/source
copying docs/source/conf.py -> mss-{__version__}/docs/source
copying docs/source/developers.rst -> mss-{__version__}/docs/source
copying docs/source/examples.rst -> mss-{__version__}/docs/source
copying docs/source/index.rst -> mss-{__version__}/docs/source
copying docs/source/installation.rst -> mss-{__version__}/docs/source
copying docs/source/support.rst -> mss-{__version__}/docs/source
copying docs/source/usage.rst -> mss-{__version__}/docs/source
copying docs/source/where.rst -> mss-{__version__}/docs/source
copying docs/source/examples/callback.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/custom_cls_image.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/fps.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/fps_multiprocessing.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/from_pil_tuple.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/linux_display_keyword.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/opencv_numpy.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/part_of_screen.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/part_of_screen_monitor_2.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/pil.py -> mss-{__version__}/docs/source/examples
copying docs/source/examples/pil_pixels.py -> mss-{__version__}/docs/source/examples
copying src/mss/__init__.py -> mss-{__version__}/src/mss
copying src/mss/__main__.py -> mss-{__version__}/src/mss
copying src/mss/base.py -> mss-{__version__}/src/mss
copying src/mss/darwin.py -> mss-{__version__}/src/mss
copying src/mss/exception.py -> mss-{__version__}/src/mss
copying src/mss/factory.py -> mss-{__version__}/src/mss
copying src/mss/linux.py -> mss-{__version__}/src/mss
copying src/mss/models.py -> mss-{__version__}/src/mss
copying src/mss/py.typed -> mss-{__version__}/src/mss
copying src/mss/screenshot.py -> mss-{__version__}/src/mss
copying src/mss/tools.py -> mss-{__version__}/src/mss
copying src/mss/windows.py -> mss-{__version__}/src/mss
copying src/mss.egg-info/PKG-INFO -> mss-{__version__}/src/mss.egg-info
copying src/mss.egg-info/SOURCES.txt -> mss-{__version__}/src/mss.egg-info
copying src/mss.egg-info/dependency_links.txt -> mss-{__version__}/src/mss.egg-info
copying src/mss.egg-info/entry_points.txt -> mss-{__version__}/src/mss.egg-info
copying src/mss.egg-info/top_level.txt -> mss-{__version__}/src/mss.egg-info
copying src/tests/bench_bgra2rgb.py -> mss-{__version__}/src/tests
copying src/tests/bench_general.py -> mss-{__version__}/src/tests
copying src/tests/conftest.py -> mss-{__version__}/src/tests
copying src/tests/test_bgra_to_rgb.py -> mss-{__version__}/src/tests
copying src/tests/test_cls_image.py -> mss-{__version__}/src/tests
copying src/tests/test_find_monitors.py -> mss-{__version__}/src/tests
copying src/tests/test_get_pixels.py -> mss-{__version__}/src/tests
copying src/tests/test_gnu_linux.py -> mss-{__version__}/src/tests
copying src/tests/test_implementation.py -> mss-{__version__}/src/tests
copying src/tests/test_issue_220.py -> mss-{__version__}/src/tests
copying src/tests/test_leaks.py -> mss-{__version__}/src/tests
copying src/tests/test_macos.py -> mss-{__version__}/src/tests
copying src/tests/test_save.py -> mss-{__version__}/src/tests
copying src/tests/test_setup.py -> mss-{__version__}/src/tests
copying src/tests/test_third_party.py -> mss-{__version__}/src/tests
copying src/tests/test_tools.py -> mss-{__version__}/src/tests
copying src/tests/test_windows.py -> mss-{__version__}/src/tests
copying src/tests/res/monitor-1024x768.raw.zip -> mss-{__version__}/src/tests/res
Writing mss-{__version__}/setup.cfg
    """

    print(output)
    for line in expected.splitlines():
        if not (line := line.strip()):
            continue
        assert line in output
    assert output.count("copying") == expected.count("copying")
    assert f"Successfully built mss-{__version__}.tar.gz" in output
    assert "warning" not in output.lower()

    check_call(CHECK)


def test_wheel():
    output = check_output(WHEEL, stderr=STDOUT, text=True)
    expected = f"""
creating build/bdist.linux-x86_64/wheel/mss-{__version__}.dist-info/WHEEL
 and adding 'build/bdist.linux-x86_64/wheel' to it
adding 'mss/__init__.py'
adding 'mss/__main__.py'
adding 'mss/base.py'
adding 'mss/darwin.py'
adding 'mss/exception.py'
adding 'mss/factory.py'
adding 'mss/linux.py'
adding 'mss/models.py'
adding 'mss/py.typed'
adding 'mss/screenshot.py'
adding 'mss/tools.py'
adding 'mss/windows.py'
adding 'mss-{__version__}.dist-info/METADATA'
adding 'mss-{__version__}.dist-info/WHEEL'
adding 'mss-{__version__}.dist-info/entry_points.txt'
adding 'mss-{__version__}.dist-info/top_level.txt'
adding 'mss-{__version__}.dist-info/RECORD'
    """

    print(output)
    for line in expected.splitlines():
        if not (line := line.strip()):
            continue
        assert line in output
    assert output.count("adding") == expected.count("adding")
    assert f"Successfully built mss-{__version__}-py3-none-any.whl" in output
    assert "warning" not in output.lower()

    check_call(CHECK)
