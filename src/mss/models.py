# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, NamedTuple

Pixel = tuple[int, int, int]
Pixels = list[tuple[Pixel, ...]]


class Monitor:
    """Represents a display monitor with its position and dimensions.

    :param left: The x-coordinate of the upper-left corner.
    :param top: The y-coordinate of the upper-left corner.
    :param width: The width of the monitor.
    :param height: The height of the monitor.
    :param is_primary: Whether this is the primary monitor.
    :param name: The device name of the monitor (platform-specific).
    """

    __slots__ = ("height", "is_primary", "left", "name", "top", "width")

    def __init__(  # noqa: PLR0913
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        *,
        is_primary: bool = False,
        name: str = "",
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.is_primary = is_primary
        self.name = name

    def __repr__(self) -> str:
        return (
            f"Monitor(left={self.left}, top={self.top}, width={self.width}, "
            f"height={self.height}, is_primary={self.is_primary}, name={self.name!r})"
        )

    def __getitem__(self, key: str) -> int | bool:
        """Provide dict-like access for backward compatibility."""
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __setitem__(self, key: str, value: int | bool) -> None:
        """Provide dict-like setitem for backward compatibility."""
        if not hasattr(self, key):
            raise KeyError(key)
        setattr(self, key, value)

    def keys(self) -> list[str]:
        """Provide dict-like keys() for backward compatibility."""
        return list(self.__slots__)

    def __contains__(self, key: str) -> bool:
        """Provide dict-like 'in' operator for backward compatibility."""
        return hasattr(self, key) and key in self.__slots__


Monitors = list[Monitor]

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
