# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypedDict, overload


class CaptureRegion(TypedDict):
    """Rectangular screen region to capture."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Monitor:
    """Monitor geometry and optional platform metadata.

    The optional metadata attributes are:

    - ``is_primary``: whether this is the primary monitor; ``None`` means
      the platform could not determine it.
    - ``name``: the human-readable device name; ``None`` means it is
      unavailable.
    - ``unique_id``: the platform-specific stable identifier; ``None``
      means it is unavailable.
    - ``output``: the Linux output name compatible with xrandr; ``None``
      means it is unavailable or does not apply to the platform.
    """

    left: int
    top: int
    width: int
    height: int
    is_primary: bool | None = None
    name: str | None = None
    unique_id: str | None = None
    output: str | None = None

    def as_capture_region(self) -> CaptureRegion:
        """Return this monitor's geometry as a capture region."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }

    @overload
    def __getitem__(self, key: Literal["left", "top", "width", "height"], /) -> int: ...

    @overload
    def __getitem__(self, key: Literal["is_primary"], /) -> bool | None: ...

    @overload
    def __getitem__(self, key: Literal["name", "unique_id", "output"], /) -> str | None: ...

    @overload
    def __getitem__(self, key: str, /) -> int | bool | str | None: ...

    def __getitem__(self, key: str, /) -> int | bool | str | None:
        """Provide temporary compatibility with string-key access."""
        if key not in {"left", "top", "width", "height", "is_primary", "name", "unique_id", "output"}:
            raise KeyError(key)
        return getattr(self, key)


Monitors = list[Monitor]

Pixel = tuple[int, int, int]
Pixels = list[tuple[Pixel, ...]]

if TYPE_CHECKING:
    from collections.abc import Callable

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
