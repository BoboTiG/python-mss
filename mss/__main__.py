# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from __future__ import print_function

import sys
from argparse import ArgumentParser

from . import __version__
from .exception import ScreenShotError
from .factory import mss


def main():
    # type: () -> int
    """ Main logic. """

    cli_args = ArgumentParser()
    cli_args.add_argument('-m', '--monitor', default=0, type=int,
                          help='the monitor to screenshot')
    cli_args.add_argument('-o', '--output', default='monitor-%d.png',
                          help='the output file name')
    cli_args.add_argument('-v', '--version', action='version',
                          version=__version__)
    parser = cli_args.parse_args(sys.argv[1:])
    kwargs = {
        'mon': parser.monitor,
        'output': parser.output,
    }

    try:
        with mss() as sct:
            for file_name in sct.save(**kwargs):
                print(file_name)
            return 0
    except ScreenShotError:
        return 1


if __name__ == '__main__':
    exit(main())
