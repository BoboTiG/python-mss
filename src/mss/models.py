# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, NamedTuple

Monitor = dict[str, Any]
Monitors = list[Monitor]

Pixel = tuple[int, int, int]
Pixels = list[tuple[Pixel, ...]]

if TYPE_CHECKING:
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
