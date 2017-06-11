# coding: utf-8
""" This is part of the MSS Python's module.
    Source: https://github.com/BoboTiG/python-mss
"""

from __future__ import print_function

from .factory import mss


def main():
    # type: () -> int
    """ Main logic. """

    with mss() as sct:
        for file_name in sct.save():
            print(file_name)
        return 0

    return 1


if __name__ == '__main__':
    exit(main())
