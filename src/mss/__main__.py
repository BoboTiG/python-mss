"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os.path
import platform
import re
import sys
from argparse import ArgumentError, ArgumentParser, Namespace
from typing import Any

from mss import MSS, __version__
from mss.exception import ScreenShotError
from mss.tools import to_png

_COORDINATES_SYNTAX = "TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP"


def _backend_cli_choices() -> list[str]:
    os_name = platform.system().lower()
    if os_name == "darwin":
        from mss import darwin  # noqa: PLC0415

        return darwin.BACKENDS
    if os_name == "linux":
        from mss import linux  # noqa: PLC0415

        return linux.BACKENDS
    if os_name == "windows":
        from mss import windows  # noqa: PLC0415

        return windows.BACKENDS
    return ["default"]


def _parse_coordinates(coordinates: str) -> tuple[int, int, int, int]:
    """Parse a capture region string.

    Supports ``TOP,LEFT,WIDTH,HEIGHT`` and X11 geometry style
    ``WIDTHxHEIGHT+LEFT+TOP`` (with optional ``-`` offsets).

    :param coordinates: Region string to parse.
    :returns: Parsed coordinates as ``(top, left, width, height)``.
    :raises ValueError: If *coordinates* does not match a supported
        syntax.
    """
    match_res = re.fullmatch(
        r"""(?x)^\s*(?:
        (?: # top, left, width, height
            (?P<top1>-?[0-9]+)\s*,\s*
            (?P<left1>-?[0-9]+)\s*,\s*
            (?P<width1>[0-9]+)\s*,\s*
            (?P<height1>[0-9]+))
        |
        (?: # WIDTHxHEIGHT+XOFF+YOFF (X11 geometry style; see X(7))
           (?P<width2>[0-9]+)\s*x\s*
           (?P<height2>[0-9]+)\s*(?P<left2sign>[+-])\s*
           (?P<left2>[0-9]+)\s*(?P<top2sign>[+-])\s*
           (?P<top2>[0-9]+))
        )\s*$""",
        coordinates,
    )
    if match_res is None:
        msg = f"Coordinates syntax: {_COORDINATES_SYNTAX}"
        raise ValueError(msg)
    if match_res["top1"] is not None:
        return (int(match_res["top1"]), int(match_res["left1"]), int(match_res["width1"]), int(match_res["height1"]))
    if match_res["top2"] is not None:
        top2 = int(match_res["top2"])
        if match_res["top2sign"] == "-":
            top2 = -top2
        left2 = int(match_res["left2"])
        if match_res["left2sign"] == "-":
            left2 = -left2
        return top2, left2, int(match_res["width2"]), int(match_res["height2"])
    msg = f"Coordinates syntax: {_COORDINATES_SYNTAX}"
    raise ValueError(msg)


def _build_parser() -> ArgumentParser:
    """Create and configure the CLI argument parser."""
    backend_choices = _backend_cli_choices()

    cli_args = ArgumentParser(prog="mss", exit_on_error=False)
    cli_args.add_argument(
        "-c",
        "--coordinates",
        default="",
        type=str,
        help=(
            "the part of the screen to capture: TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP; "
            "negative TOP or LEFT are insets from the bottom or right edge"
        ),
    )
    cli_args.add_argument(
        "-l",
        "--level",
        default=6,
        type=int,
        choices=list(range(10)),
        help="the PNG compression level",
    )
    cli_args.add_argument("-m", "--monitor", default=0, type=int, help="the monitor to screenshot")
    cli_args.add_argument("-o", "--output", default="monitor-{mon}.png", help="the output file name")
    cli_args.add_argument("--with-cursor", default=None, action="store_true", help="include the cursor")
    cli_args.add_argument(
        "-q",
        "--quiet",
        default=False,
        action="store_true",
        help="do not print created files",
    )
    cli_args.add_argument(
        "-b", "--backend", default="default", choices=backend_choices, help="platform-specific backend to use"
    )
    cli_args.add_argument("-v", "--version", action="version", version=__version__)
    return cli_args


def _prepare_grab_options(options: Namespace) -> tuple[int, str, dict[str, int] | None]:
    """Build grab options derived from parsed CLI arguments."""
    monitor_index = int(options.monitor)
    output_template = str(options.output)
    if not options.coordinates:
        return monitor_index, output_template, None

    top, left, width, height = _parse_coordinates(str(options.coordinates))
    coordinates = {
        "top": int(top),
        "left": int(left),
        "width": int(width),
        "height": int(height),
    }
    if options.output == "monitor-{mon}.png":
        output_template = "sct-{top}x{left}_{width}x{height}.png"
    return monitor_index, output_template, coordinates


def _build_mss_kwargs(options: Namespace) -> dict[str, Any]:
    """Build keyword arguments passed to ``MSS`` constructor."""
    mss_kwargs: dict[str, str | bool] = {"backend": options.backend}
    if options.with_cursor is not None:
        mss_kwargs["with_cursor"] = options.with_cursor
    return mss_kwargs


def _capture_and_save(
    sct: MSS,
    *,
    options: Namespace,
    monitor_index: int,
    output_template: str,
    coordinates: dict[str, int] | None,
) -> None:
    """Capture screenshots and write output files."""
    if coordinates is not None:
        if coordinates["top"] < 0:
            coordinates["top"] = sct.monitors[monitor_index]["height"] + coordinates["top"]
        if coordinates["left"] < 0:
            coordinates["left"] = sct.monitors[monitor_index]["width"] + coordinates["left"]
        output = output_template.format(**coordinates)
        sct_img = sct.grab(coordinates)
        to_png(sct_img.rgb, sct_img.size, level=options.level, output=output)
        if not options.quiet:
            print(os.path.realpath(output))
        return

    for file_name in sct.save(mon=monitor_index, output=output_template):
        if not options.quiet:
            print(os.path.realpath(file_name))


def main(*args: str) -> int:
    """Main logic."""
    cli_args = _build_parser()

    try:
        options = cli_args.parse_args(args or None)
    except ArgumentError as e:
        # By default, parse_args will print and the error and exit.  We return instead of exiting, to make unit testing
        # easier.
        cli_args.print_usage(sys.stderr)
        print(f"{cli_args.prog}: error: {e}", file=sys.stderr)
        return 2
    try:
        monitor_index, output_template, coordinates = _prepare_grab_options(options)
    except ValueError:
        print(f"Coordinates syntax: {_COORDINATES_SYNTAX}")
        return 2

    if options.with_cursor is not None and platform.system().lower() != "linux":
        if not options.quiet:
            print("[WARNING] --with-cursor is only supported on Linux; ignoring.", file=sys.stderr)
        options.with_cursor = None

    mss_kwargs = _build_mss_kwargs(options)

    try:
        with MSS(**mss_kwargs) as sct:
            _capture_and_save(
                sct,
                options=options,
                monitor_index=monitor_index,
                output_template=output_template,
                coordinates=coordinates,
            )
            return 0
    except ScreenShotError:
        if options.quiet:
            return 1
        raise


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ScreenShotError as exc:
        print("[ERROR]", exc)
        sys.exit(1)
