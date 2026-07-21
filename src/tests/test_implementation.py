"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

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
from mss.__main__ import _parse_coordinates
from mss.__main__ import main as entry_point
from mss.base import MSS, MSSImplementation
from mss.exception import ScreenShotError
from mss.screenshot import ScreenShot
from tests.thread_helpers import run_threads

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from mss.models import Monitor, Monitors, Size

try:
    from datetime import UTC
except ImportError:
    # Python < 3.11
    from datetime import timezone

    UTC = timezone.utc


class MSS0(MSSImplementation):
    """Nothing implemented."""


class MSS1(MSSImplementation):
    """Only `grab()` implemented."""

    def grab(self, monitor: Monitor) -> None:  # type: ignore[override]
        pass


class MSS2(MSSImplementation):
    """Only `monitor` implemented."""

    def monitors(self) -> Monitors:
        return []


class MSSCloseRaises(MSSImplementation):
    """Implementation whose cleanup fails."""

    def __init__(self, close_error: Exception) -> None:
        super().__init__()
        self.close_error = close_error

    def cursor(self) -> None:
        pass

    def grab(self, _: Monitor) -> bytearray | tuple[bytearray, Size]:
        return bytearray()

    def monitors(self) -> Monitors:
        return []

    def close(self) -> None:
        raise self.close_error


@pytest.mark.parametrize(
    "cls",
    [
        pytest.param(MSS0, id="no_methods"),
        pytest.param(MSS1, id="grab_only"),
        pytest.param(MSS2, id="monitors_only"),
    ],
)
def test_incomplete_class(cls: type[MSSImplementation]) -> None:
    with pytest.raises(TypeError):
        cls()


def test_context_manager_keeps_body_exception_when_close_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    body_error = RuntimeError("body failed")
    close_error = RuntimeError("close failed")
    impl = MSSCloseRaises(close_error)
    monkeypatch.setattr("mss.base._choose_impl", lambda **_kwargs: impl)

    with pytest.raises(RuntimeError, match="body failed") as exc, MSS():
        raise body_error

    assert exc.value is body_error


def test_context_manager_reports_close_failure_after_clean_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    close_error = RuntimeError("close failed")
    impl = MSSCloseRaises(close_error)
    monkeypatch.setattr("mss.base._choose_impl", lambda **_kwargs: impl)

    with pytest.raises(RuntimeError, match="close failed") as exc, MSS():
        pass

    assert exc.value is close_error


def test_bad_monitor(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct, pytest.raises(ScreenShotError):
        sct.shot(mon=222)


def test_repr(mss_impl: Callable[..., MSS]) -> None:
    box = {"top": 0, "left": 0, "width": 10, "height": 10}
    expected_box = {"top": 0, "left": 0, "width": 10, "height": 10}
    with mss_impl() as sct:
        img = sct.grab(box)
    ref = ScreenShot(bytearray(b"BGRA" * 100), expected_box)
    assert repr(img) == repr(ref)


def test_factory_no_backend() -> None:
    with mss.MSS() as sct:
        assert isinstance(sct, MSS)


def test_factory_current_system(backend: str) -> None:
    with mss.MSS(backend=backend) as sct:
        assert isinstance(sct, MSS)


def test_factory_unknown_system(backend: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(platform, "system", lambda: "Chuck Norris")
    with pytest.raises(ScreenShotError) as exc:
        mss.MSS(backend=backend)
    monkeypatch.undo()

    error = exc.value.args[0]
    assert error == "System 'chuck norris' not (yet?) implemented."


@pytest.fixture
def reset_sys_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [])


@pytest.mark.usefixtures("reset_sys_argv")
@pytest.mark.parametrize(
    "with_cursor",
    [
        pytest.param(False, id="without_cursor"),
        pytest.param(True, id="with_cursor"),
    ],
)
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
        for opts in zip(["-m 1", "--monitor=1"], ["-q", "--quiet"], strict=False):
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
            with mss.MSS() as sct:
                for mon, (monitor, line) in enumerate(
                    zip(sct.monitors[1:], captured.out.splitlines(), strict=False),
                    1,
                ):
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

    @pytest.mark.parametrize("coordinates", ["2,12,40,67", "40x67+12+2"])
    def test_coordinates_capture(self, with_cursor: bool, capsys: pytest.CaptureFixture, coordinates: str) -> None:
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
            assert captured.out == "Coordinates syntax: TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP\n"

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
@patch("mss.base.MSS.monitors", new=[])
@pytest.mark.parametrize(
    "quiet",
    [
        pytest.param(False, id="verbose_mode"),
        pytest.param(True, id="quiet_mode"),
    ],
)
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


@pytest.mark.parametrize(
    ("coordinates", "expected"),
    [
        pytest.param(" 15,14,0012,13 ", (15, 14, 12, 13), id="comma_pos_top_pos_left"),
        pytest.param("-15, 0014,12,0013", (-15, 14, 12, 13), id="comma_neg_top_pos_left"),
        pytest.param("0015 , -14 , 12 , 13", (15, -14, 12, 13), id="comma_pos_top_neg_left"),
        pytest.param(" -0015,-14,12,0013  ", (-15, -14, 12, 13), id="comma_neg_top_neg_left"),
        pytest.param("12x13+14+15", (15, 14, 12, 13), id="x_pos_top_pos_left"),
        pytest.param(" 0012 x 13 - 14 + 15 ", (15, -14, 12, 13), id="x_pos_top_neg_left"),
        pytest.param("12x0013+0014-15", (-15, 14, 12, 13), id="x_neg_top_pos_left"),
        pytest.param(" 12 x 13 - 0014 - 0015 ", (-15, -14, 12, 13), id="x_neg_top_neg_left"),
    ],
)
def test_parse_coordinates_valid(coordinates: str, expected: tuple[int, int, int, int]) -> None:
    assert _parse_coordinates(coordinates) == expected


@pytest.mark.parametrize(
    "coordinates",
    [
        pytest.param("1,2,-3,4", id="comma_negative_width"),
        pytest.param("1,2,3,-4", id="comma_negative_height"),
        pytest.param("-0012x0013+0014+0015", id="x_negative_width"),
        pytest.param("0012x-0013+0014+0015", id="x_negative_height"),
        pytest.param("0x10,2,30,40", id="comma_hex_prefix"),
        pytest.param("30x40+0x10+2", id="x_hex_prefix"),
    ],
)
def test_parse_coordinates_invalid(coordinates: str) -> None:
    with pytest.raises(ValueError, match=r"(?i)coordinates syntax"):
        _parse_coordinates(coordinates)


def test_grab_with_tuple(mss_impl: Callable[..., MSS]) -> None:
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


def test_grab_with_invalid_tuple(mss_impl: Callable[..., MSS]) -> None:
    with mss_impl() as sct:
        # Remember that rect tuples are PIL-style: (left, top, right, bottom)
        # Negative left/top coordinates are valid for multi-monitor setups
        # where monitors can be positioned to the left of or above the primary.

        # Negative width (right < left)
        negative_box = (100, 100, 50, 500)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)

        # Negative height (bottom < top)
        negative_box = (100, 100, 500, 50)
        with pytest.raises(ScreenShotError):
            sct.grab(negative_box)


def test_grab_with_tuple_percents(mss_impl: Callable[..., MSS]) -> None:
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

        checkpoint: dict[threading.Thread, bool] = {}
        run_threads(record, record, start_delay=0.5)
        assert len(checkpoint) == 2

    def test_issue_169(self, backend: str) -> None:
        """Regression test for issue #169."""

        def do_grab() -> None:
            with mss.MSS(backend=backend) as sct:
                sct.grab(sct.monitors[1])

        self.run_test(do_grab)

    def test_same_object_multiple_threads(self, backend: str) -> None:
        """Ensure that the same MSS object can be used by multiple threads.

        This also implicitly tests that it can be used on a thread
        different than the one that created it.
        """
        if backend == "xlib":
            pytest.skip("The xlib backend does not support this ability")
        with mss.MSS(backend=backend) as sct:
            self.run_test(lambda: sct.grab(sct.monitors[1]))
