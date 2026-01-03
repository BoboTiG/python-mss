# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from typing import Any, Callable, NamedTuple

Monitor = dict[str, int]
Monitors = list[Monitor]

Pixel = tuple[int, int, int]
Pixels = list[tuple[Pixel, ...]]

CFunctions = dict[str, tuple[str, list[Any], Any]]
CFunctionsErrChecked = dict[str, tuple[str, list[Any], Any, Callable | None]]


class Pos(NamedTuple):
    #: The horizontal X coordinate of the position.
    left: int
    #: The vertical Y coordinate of the position.
    top: int


class Size(NamedTuple):
    #: The horizontal X width.
    width: int
    #: The vertical Y height.
    height: int
