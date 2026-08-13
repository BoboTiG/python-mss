"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os.path
import platform
import re
import sys
from argparse import ArgumentError, ArgumentParser, Namespace
from typing import Any, NamedTuple

from mss import MSS, __version__
from mss.models import Monitor
from mss.exception import ScreenShotError
from mss.tools import to_png

_COORDINATES_SYNTAX = "TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP"


class _CoordsWithEdges(NamedTuple):
    top: int
    left: int
    width: int
    height: int
    from_bottom: bool
    from_right: bool


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


def _parse_xgeom_coordinate(sign1: str, sign2: str | None, magnitude: str) -> tuple[int, bool]:
    """Parse a TOP or LEFT coordinate of an X-style geometry.

    As in XParseGeometry, the LEFT and/or TOP coordinates may be
    preceded by ``-`` instead of ``+``.  This means that they should
    be interpreted as offsets from the bottom or right, rather than
    the top or left.

    Additionally, the values themselves may be negative.  On X, this
    normally indicates that they may be partially off-screen.  On
    Windows and macOS, these are normal coordinates, since those
    systems always place the primary monitor at 0,0.

    When using values from the bottom or right, the height or width
    should be added by the caller as additional offsets.  In other
    words, a region with a width of 100 pixels, with a 25-pixel offset
    from the right, should still have all 100 onscreen pixels
    onscreen, with 25 pixels between the region and the right edge of
    the screen.

    Examples for the TOP coordinate (these are exhaustive):
    - ``+25`` or ``++25``: 25 pixels from the top
    - ``-25`` or ``-+25``: 25 pixels from the bottom
    - ``+-25``: 25 pixels extend above the top
    - ``--25``: 25 pixels extend below the bottom

    The returned int is negative if the edge is meant to be offscreen,
    and the returned bool is True if the edge is meant to be from the
    opposite border.
    """
    assert sign1 in {"+", "-"}  # noqa: S101
    assert sign2 in {"+", "-", None}  # noqa: S101
    assert "+" not in magnitude  # noqa: S101
    assert "-" not in magnitude  # noqa: S101

    signs = sign1 if sign2 is None else sign1 + sign2

    magnitude_value = int(magnitude)
    if signs in {"+", "++"}:
        return magnitude_value, False
    if signs in {"-", "-+"}:
        return magnitude_value, True
    if signs == "+-":
        return -magnitude_value, False
    if signs == "--":
        return -magnitude_value, True
    # This is an internal error.
    msg = "Invalid signs"
    raise ValueError(msg)


def _parse_coordinates(coordinates: str) -> _CoordsWithEdges:
    """Parse a capture region string.

    Supports ``TOP,LEFT,WIDTH,HEIGHT`` and X11 geometry style
    ``WIDTHxHEIGHT+LEFT+TOP`` (with optional ``-`` special handling).

    See _parse_xgeom_coordinate for notes about how negative values and
    the

    :param coordinates: Region string to parse.
    :returns: Parsed coordinates as
        ``(top, left, width, height, from_bottom, from_right)``.
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
           (?P<height2>[0-9]+)\s*
           (?P<left2sign1>[+-])\s*(?P<left2sign2>[+-]\s*)?(?P<left2>[0-9]+)\s*
           (?P<top2sign1>[+-])\s*(?P<top2sign2>[+-]\s*)?(?P<top2>[0-9]+))
        )\s*$""",
        coordinates,
    )
    if match_res is None:
        msg = f"Coordinates syntax: {_COORDINATES_SYNTAX}"
        raise ValueError(msg)

    if match_res["top1"] is not None:
        return _CoordsWithEdges(
            top=int(match_res["top1"]),
            left=int(match_res["left1"]),
            width=int(match_res["width1"]),
            height=int(match_res["height1"]),
            from_bottom=False,
            from_right=False,
        )

    if match_res["top2"] is not None:
        left, from_right = _parse_xgeom_coordinate(match_res["left2sign1"], match_res["left2sign2"], match_res["left2"])
        top, from_bottom = _parse_xgeom_coordinate(match_res["top2sign1"], match_res["top2sign2"], match_res["top2"])
        return _CoordsWithEdges(
            top=top,
            left=left,
            width=int(match_res["width2"]),
            height=int(match_res["height2"]),
            from_bottom=from_bottom,
            from_right=from_right,
        )

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
        help="the part of the screen to capture: TOP,LEFT,WIDTH,HEIGHT or WIDTHxHEIGHT+LEFT+TOP",
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


def _prepare_grab_options(options: Namespace) -> tuple[int, str, _CoordsWithEdges | None]:
    """Build grab options derived from parsed CLI arguments."""
    monitor_index = int(options.monitor)
    output_template = str(options.output)
    if options.coordinates is None:
        return monitor_index, output_template, None

    coordinates = _parse_coordinates(str(options.coordinates))
    if options.output == "monitor-{mon}.png":
        output_template = "sct-{top}x{left}_{width}x{height}.png"
    return monitor_index, output_template, coordinates


def _build_mss_kwargs(options: Namespace) -> dict[str, Any]:
    """Build keyword arguments passed to ``MSS`` constructor."""
    mss_kwargs: dict[str, str | bool] = {"backend": options.backend}
    if options.with_cursor is not None:
        mss_kwargs["with_cursor"] = options.with_cursor
    return mss_kwargs


def _normalize_capture_region(coordinates: _CoordsWithEdges, reference: Monitor, bounds: Monitor) -> Monitor:
    print(coordinates)
    print(reference)
    print(bounds)

    if coordinates.from_bottom:
        top = reference["top"] + reference["height"] - coordinates.top - coordinates.height
    else:
        top = reference["top"] + coordinates.top
    if coordinates.from_right:
        left = reference["left"] + reference["width"] - coordinates.left - coordinates.width
    else:
        left = reference["left"] + coordinates.left

    # It's easier to crop to the bounds if we work on bottom and right.
    bounds_bottom = bounds["top"] + bounds["height"]
    bounds_right = bounds["left"] + bounds["width"]
    bottom = min(top + coordinates.height, bounds_bottom)
    right = min(left + coordinates.width, bounds_right)
    top = max(top, bounds["top"])
    left = max(left, bounds["left"])

    rv = {
        "top": top,
        "left": left,
        "height": bottom - top,
        "width": right - left,
    }
    print(rv)
    return rv


def _capture_and_save(
    sct: MSS,
    *,
    options: Namespace,
    monitor_index: int,
    output_template: str,
    coordinates: _CoordsWithEdges | None,
) -> None:
    """Capture screenshots and write output files."""
    if coordinates is not None:
        desktop = sct.monitors[0]
        mon = sct.monitors[monitor_index]
        capture_region = _normalize_capture_region(coordinates, sct.monitors[monitor_index], sct.monitors[0])
        output = output_template.format(**capture_region)
        sct_img = sct.grab(capture_region)
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
