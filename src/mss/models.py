"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from typing import Any, Dict, List, NamedTuple, Tuple

Monitor = Dict[str, int]
Monitors = List[Monitor]

Pixel = Tuple[int, int, int]
Pixels = List[Tuple[Pixel, ...]]

CFunctions = Dict[str, Tuple[str, List[Any], Any]]


class Pos(NamedTuple):
    left: int
    top: int


class Size(NamedTuple):
    width: int
    height: int
