"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from collections.abc import Generator
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import pytest


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


@pytest.fixture(scope="session")
def raw() -> bytes:
    file = Path(__file__).parent / "res" / "monitor-1024x768.raw.zip"
    with ZipFile(file) as fh:
        data = fh.read(file.with_suffix("").name)

    assert sha256(data).hexdigest() == "d86ed4366d5a882cfe1345de82c87b81aef9f9bf085f4c42acb6f63f3967eccd"
    return data
