# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from __future__ import print_function

import os.path
import sys
from argparse import ArgumentParser

from . import __version__
from .exception import ScreenShotError
from .factory import mss


def main(args=None):
    # type: (Optional[List[str]]) -> int
    """ Main logic. """

    cli_args = ArgumentParser()
    cli_args.add_argument('-m', '--monitor', default=0, type=int,
                          help='the monitor to screen shot')
    cli_args.add_argument('-o', '--output', default='monitor-{mon}.png',
                          help='the output file name')
    cli_args.add_argument('-q', '--quiet', default=False, action='store_true',
                          help='Do not print created files')
    cli_args.add_argument('-v', '--version', action='version',
                          version=__version__)

    options = cli_args.parse_args(args)
    kwargs = {
        'mon': options.monitor,
        'output': options.output,
    }

    try:
        with mss() as sct:
            for file_name in sct.save(**kwargs):
                if not options.quiet:
                    print(os.path.realpath(file_name))
            return 0
    except ScreenShotError:
        return 1


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
