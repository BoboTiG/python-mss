"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import os.path
import platform
import sys
from argparse import ArgumentError, ArgumentParser

from mss import MSS, __version__
from mss.exception import ScreenShotError
from mss.tools import to_png


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


def main(*args: str) -> int:  # noqa: PLR0912
    """Main logic."""
    backend_choices = _backend_cli_choices()

    cli_args = ArgumentParser(prog="mss", exit_on_error=False)
    cli_args.add_argument(
        "-c",
        "--coordinates",
        default="",
        type=str,
        help="the part of the screen to capture: top, left, width, height",
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

    try:
        options = cli_args.parse_args(args or None)
    except ArgumentError as e:
        # By default, parse_args will print and the error and exit.  We
        # return instead of exiting, to make unit testing easier.
        cli_args.print_usage(sys.stderr)
        print(f"{cli_args.prog}: error: {e}", file=sys.stderr)
        return 2
    grab_kwargs = {"mon": options.monitor, "output": options.output}
    if options.coordinates:
        try:
            top, left, width, height = options.coordinates.split(",")
        except ValueError:
            print("Coordinates syntax: top, left, width, height")
            return 2

        grab_kwargs["mon"] = {
            "top": int(top),
            "left": int(left),
            "width": int(width),
            "height": int(height),
        }
        if options.output == "monitor-{mon}.png":
            grab_kwargs["output"] = "sct-{top}x{left}_{width}x{height}.png"

    if options.with_cursor is not None and platform.system().lower() != "linux":
        if not options.quiet:
            print("[WARNING] --with-cursor is only supported on Linux; ignoring.", file=sys.stderr)
        options.with_cursor = None

    mss_kwargs = {"backend": options.backend}
    if options.with_cursor is not None:
        mss_kwargs["with_cursor"] = options.with_cursor

    try:
        with MSS(**mss_kwargs) as sct:
            if options.coordinates:
                output = grab_kwargs["output"].format(**grab_kwargs["mon"])
                sct_img = sct.grab(grab_kwargs["mon"])
                to_png(sct_img.rgb, sct_img.size, level=options.level, output=output)
                if not options.quiet:
                    print(os.path.realpath(output))
            else:
                for file_name in sct.save(**grab_kwargs):
                    if not options.quiet:
                        print(os.path.realpath(file_name))
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
