"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import glob
import os
import platform
from collections.abc import Generator
from hashlib import md5
from pathlib import Path
from zipfile import ZipFile

import pytest

from mss import mss


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
    for fname in glob.glob("*.png"):
        print(f"Deleting {fname!r} ...")
        os.unlink(fname)

    for fname in glob.glob("*.png.old"):
        print(f"Deleting {fname!r} ...")
        os.unlink(fname)


@pytest.fixture(scope="module", autouse=True)
def _before_tests() -> None:
    purge_files()


@pytest.fixture(scope="session")
def raw() -> bytes:
    file = Path(__file__).parent / "res" / "monitor-1024x768.raw.zip"
    with ZipFile(file) as fh:
        data = fh.read(file.with_suffix("").name)

    assert md5(data).hexdigest() == "125696266e2a8f5240f6bc17e4df98c6"
    return data


@pytest.fixture(scope="session")
def pixel_ratio() -> int:
    """Get the pixel, used to adapt test checks."""
    if platform.system().lower() != "darwin":
        return 1

    # Grab a 1x1 screenshot
    region = {"top": 0, "left": 0, "width": 1, "height": 1}

    with mss() as sct:
        # On macOS with Retina display, the width can be 2 instead of 1
        return sct.grab(region).size[0]
