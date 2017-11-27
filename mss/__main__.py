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
from .tools import to_png


def main(args=None):
    # type: (Optional[List[str]]) -> int
    """ Main logic. """

    cli_args = ArgumentParser()
    cli_args.add_argument('-c', '--coordinates', default='', type=str,
                          help='the part of the screen to capture:'
                               ' top,left,width,height')
    cli_args.add_argument('-m', '--monitor', default=0, type=int,
                          help='the monitor to screen shot')
    cli_args.add_argument('-o', '--output', default='monitor-{mon}.png',
                          help='the output file name')
    cli_args.add_argument('-q', '--quiet', default=False, action='store_true',
                          help='do not print created files')
    cli_args.add_argument('-v', '--version', action='version',
                          version=__version__)

    options = cli_args.parse_args(args)
    kwargs = {
        'mon': options.monitor,
        'output': options.output,
    }
    if options.coordinates:
        top, left, width, height = map(int, options.coordinates.split(','))
        kwargs['mon'] = {
            'top': top,
            'left': left,
            'width': width,
            'height': height,
        }
        kwargs['output'] = 'sct-{top}x{left}_{width}x{height}.png'

    try:
        with mss() as sct:
            if options.coordinates:
                output = kwargs['output'].format(**kwargs['mon'])
                sct_img = sct.grab(kwargs['mon'])
                to_png(sct_img.rgb, sct_img.size, output)
                if not options.quiet:
                        print(os.path.realpath(output))
            else:
                for file_name in sct.save(**kwargs):
                    if not options.quiet:
                        print(os.path.realpath(file_name))
            return 0
    except ScreenShotError:
        return 1


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
