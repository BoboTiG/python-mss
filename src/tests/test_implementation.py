"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

import os
import platform
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

import mss
from mss.__main__ import main as entry_point
from mss.base import MSSBase
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot

if TYPE_CHECKING:  # pragma: nocover
    from collections.abc import Callable
    from typing import Any

    from mss.models import Monitor

try:
    from datetime import UTC
except ImportError:
    # Python < 3.11
    from datetime import timezone

    UTC = timezone.utc


class MSS0(MSSBase):
    """Nothing implemented."""


class MSS1(MSSBase):
    """Only `grab()` implemented."""

    def grab(self, monitor: Monitor) -> None:  # type: ignore[override]
        pass


class MSS2(MSSBase):
    """Only `monitor` implemented."""

    @property
    def monitors(self) -> list:
        return []


@pytest.mark.parametrize("cls", [MSS0, MSS1, MSS2])
def test_incomplete_class(cls: type[MSSBase]) -> None:
    with pytest.raises(TypeError):
        cls()


def test_bad_monitor(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct, pytest.raises(ScreenShotError):
        sct.shot(mon=222)


def test_repr(mss_impl: Callable[..., MSSBase]) -> None:
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    expected_box = {"top": 0, "left": 0, "width": 10, "height": 10}
    with mss_impl() as sct:
        img = sct.grab(box)
    ref = ScreenShot(bytearray(b"42"), expected_box)
    assert repr(img) == repr(ref)


def test_factory_no_backend() -> None:
    with mss.mss() as sct:
        assert isinstance(sct, MSSBase)


def test_factory_current_system(backend: str) -> None:
    with mss.mss(backend=backend) as sct:
        assert isinstance(sct, MSSBase)


def test_factory_unknown_system(backend: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Chuck Norris")
    with pytest.raises(ScreenShotError) as exc:
        mss.mss(backend=backend)
    monkeypatch.undo()

    error = exc.value.args[0]
    assert error == "System 'chuck norris' not (yet?) implemented."


@pytest.fixture
def reset_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [])


@pytest.mark.usefixtures("reset_sys_argv")
@pytest.mark.parametrize("with_cursor", [False, True])
class TestEntryPoint:
    """CLI entry-point scenarios split into focused tests."""

    @staticmethod
    def _run_main(with_cursor: bool, *args: str, ret: int = 0) -> None:
        if with_cursor:
            args = (*args, "--with-cursor")
        assert entry_point(*args) == ret

    def test_no_arguments(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        self._run_main(with_cursor)
        captured = capsys.readouterr()
        for mon, line in enumerate(captured.out.splitlines(), 1):
            filename = Path(f"monitor-{mon}.png")
            assert line.endswith(filename.name)
            assert filename.is_file()
            filename.unlink()

    def test_monitor_option_and_quiet(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        file = Path("monitor-1.png")
        filename: Path | None = None
        for opt in ("-m", "--monitor"):
            self._run_main(with_cursor, opt, "1")
            captured = capsys.readouterr()
            assert captured.out.endswith(f"{file.name}\n")
            filename = Path(captured.out.rstrip())
            assert filename.is_file()
            filename.unlink()

        assert filename is not None
        for opts in zip(["-m 1", "--monitor=1"], ["-q", "--quiet"]):
            self._run_main(with_cursor, *opts)
            captured = capsys.readouterr()
            assert not captured.out
            assert filename.is_file()
            filename.unlink()

    def test_custom_output_pattern(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        fmt = "sct-{mon}-{width}x{height}.png"
        for opt in ("-o", "--out"):
            self._run_main(with_cursor, opt, fmt)
            captured = capsys.readouterr()
            with mss.mss(display=os.getenv("DISPLAY")) as sct:
                for mon, (monitor, line) in enumerate(zip(sct.monitors[1:], captured.out.splitlines()), 1):
                    filename = Path(fmt.format(mon=mon, **monitor))
                    assert line.endswith(filename.name)
                    assert filename.is_file()
                    filename.unlink()

    def test_output_pattern_with_date(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        fmt = "sct_{mon}-{date:%Y-%m-%d}.png"
        for opt in ("-o", "--out"):
            self._run_main(with_cursor, "-m 1", opt, fmt)
            filename = Path(fmt.format(mon=1, date=datetime.now(tz=UTC)))
            captured = capsys.readouterr()
            assert captured.out.endswith(f"{filename}\n")
            assert filename.is_file()
            filename.unlink()

    def test_coordinates_capture(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        coordinates = "2,12,40,67"
        filename = Path("sct-2x12_40x67.png")
        for opt in ("-c", "--coordinates"):
            self._run_main(with_cursor, opt, coordinates)
            captured = capsys.readouterr()
            assert captured.out.endswith(f"{filename}\n")
            assert filename.is_file()
            filename.unlink()

    def test_invalid_coordinates(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        coordinates = "2,12,40"
        for opt in ("-c", "--coordinates"):
            self._run_main(with_cursor, opt, coordinates, ret=2)
            captured = capsys.readouterr()
            assert captured.out == "Coordinates syntax: top, left, width, height\n"

    def test_backend_option(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        backend = "default"
        for opt in ("-b", "--backend"):
            self._run_main(with_cursor, opt, backend, "-m1")
            captured = capsys.readouterr()
            filename = Path(captured.out.rstrip())
            assert filename.is_file()
            filename.unlink()

    def test_invalid_backend_option(self, with_cursor: bool, capsys: pytest.CaptureFixture) -> None:
        backend = "chuck_norris"
        for opt in ("-b", "--backend"):
            self._run_main(with_cursor, opt, backend, "-m1", ret=2)
            captured = capsys.readouterr()
            assert "argument -b/--backend: invalid choice: 'chuck_norris' (choose from" in captured.err


@patch.object(sys, "argv", new=[])  # Prevent side effects while testing
@patch("mss.base.MSSBase.monitors", new=[])
@pytest.mark.parametrize("quiet", [False, True])
def test_entry_point_error(quiet: bool, capsys: pytest.CaptureFixture) -> None:
    def main(*args: str) -> int:
        if quiet:
            args = (*args, "--quiet")
        return entry_point(*args)

    if quiet:
        assert main() == 1
        captured = capsys.readouterr()
        assert not captured.out
        assert not captured.err
    else:
        with pytest.raises(ScreenShotError):
            main()


def test_entry_point_with_no_argument(capsys: pytest.CaptureFixture) -> None:
    # Make sure to fail if arguments are not handled
    with (
        patch("mss.factory.mss", new=Mock(side_effect=RuntimeError("Boom!"))),
        patch.object(sys, "argv", ["mss", "--help"]),
        pytest.raises(SystemExit) as exc,
    ):
        entry_point()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    assert not captured.err
    assert "usage: mss" in captured.out


def test_grab_with_tuple(mss_impl: Callable[..., MSSBase]) -> None:
    left = 100
    top = 100
    right = 500
    lower = 500
    width = right - left  # 400px width
    height = lower - top  # 400px height

    with mss_impl() as sct:
        # PIL like
        box = (left, top, right, lower)
        im = sct.grab(box)
        assert im.size == (width, height)

        # MSS like
        box2 = {"left": left, "top": top, "width": width, "height": height}
        im2 = sct.grab(box2)
        assert im.size == im2.size
        assert im.pos == im2.pos
        assert im.rgb == im2.rgb


def test_grab_with_invalid_tuple(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        # Remember that rect tuples are PIL-style: (left, top, right, bottom)

        # Negative top
        negative_box = (100, -100, 500, 500)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)

        # Negative left
        negative_box = (-100, 100, 500, 500)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)

        # Negative width (but right > 0)
        negative_box = (100, 100, 50, 500)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)

        # Negative height (but bottom > 0)
        negative_box = (100, 100, 500, 50)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)


def test_grab_with_tuple_percents(mss_impl: Callable[..., MSSBase]) -> None:
    with mss_impl() as sct:
        monitor = sct.monitors[1]
        left = monitor["left"] + monitor["width"] * 5 // 100  # 5% from the left
        top = monitor["top"] + monitor["height"] * 5 // 100  # 5% from the top
        right = left + 500  # 500px
        lower = top + 500  # 500px
        width = right - left
        height = lower - top

        # PIL like
        box = (left, top, right, lower)
        im = sct.grab(box)
        assert im.size == (width, height)

        # MSS like
        box2 = {"left": left, "top": top, "width": width, "height": height}
        im2 = sct.grab(box2)
        assert im.size == im2.size
        assert im.pos == im2.pos
        assert im.rgb == im2.rgb


class TestThreadSafety:
    def run_test(self, do_grab: Callable[[], Any]) -> None:
        def record() -> None:
            """Record for one second."""
            start_time = time.time()
            while time.time() - start_time < 1:
                do_grab()

            checkpoint[threading.current_thread()] = True

        checkpoint: dict = {}
        t1 = threading.Thread(target=record)
        t2 = threading.Thread(target=record)

        t1.start()
        time.sleep(0.5)
        t2.start()

        t1.join()
        t2.join()

        assert len(checkpoint) == 2

    def test_issue_169(self, backend: str) -> None:
        """Regression test for issue #169."""

        def do_grab() -> None:
            with mss.mss(backend=backend) as sct:
                sct.grab(sct.monitors[1])

        self.run_test(do_grab)

    def test_same_object_multiple_threads(self, backend: str) -> None:
        """Ensure that the same MSS object can be used by multiple threads.

        This also implicitly tests that it can be used on a thread
        different than the one that created it.
        """
        if backend == "xlib":
            pytest.skip("The xlib backend does not support this ability")
        with mss.mss(backend=backend) as sct:
            self.run_test(lambda: sct.grab(sct.monitors[1]))
