# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, overload


@dataclass(slots=True)
class Region:
    """Rectangular screen region."""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Monitor:
    """Monitor geometry and optional platform metadata.

    .. seealso::
       - :py:attr:`.MSS.monitors`
       - :py:attr:`.MSS.primary_monitor`

    .. version-changed:: 11.0.0
       Prior to this version, ``Monitor`` was an alias for ``dict[str, int]``.
       In MSS 11, it is still possible to access attributes with dict-style
       string-key access, such as ``monitor["left"]``, but this
       behavior is deprecated and will be removed in a later version.
    """

    #: The monitor's left edge within the entire virtual desktop.
    left: int
    #: The monitor's top edge within the entire virtual desktop.
    top: int
    width: int
    height: int
    #: The human-readable name of this monitor, typically the brand
    #: and model.
    #:
    #: .. version-added:: 10.2.0
    name: str | None = None
    #: Whether this is the primary monitor, according to the operating
    #: system.  If MSS can't determine the primary monitor, this will
    #: be ``None`` for all monitors, although
    #: :py:attr:`.MSS.primary_monitor` will still return a monitor
    #: (the first one).
    #:
    #: .. version-added:: 10.2.0
    is_primary: bool | None = None
    #: The platform-specific stable identifier.  This is
    #: generally stable across reboots, or ordinary disconnection /
    #: reconnection, but may change when the display hardware or
    #: connection topology changes.
    #:
    #: .. version-added:: 10.2.0
    unique_id: str | None = None
    #: The short output name, for interfacing with other tools.  This
    #: is only currently populated by Linux, where it is the name used
    #: by xrandr.
    #:
    #: .. version-added:: 10.2.0
    output: str | None = None

    def as_region(self) -> Region:
        """Return this monitor's geometry as a capture region.

        .. version-added:: 11.0.0
            Prior to this version, a Region and a Monitor were effectively
            the same: a dict with left, top, width, and height entries.        
        """
        return Region(left=self.left, top=self.top, width=self.width, height=self.height)

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
