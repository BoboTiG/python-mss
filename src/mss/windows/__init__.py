"""Microsoft Windows backend dispatcher for MSS screenshot implementations."""

from __future__ import annotations

import warnings
from typing import Any

from mss.base import MSS as _MSS
from mss.base import MSSImplementation
from mss.exception import ScreenShotError

# Re-export the GDI implementation so existing code that references
# ``mss.windows.MSSImplWindows`` keeps working.
from mss.windows.gdi import MSSImplWindows

__all__ = ["MSS"]

BACKENDS = ["default"]


class MSS(_MSS):
    """Deprecated Microsoft Windows compatibility constructor.

    Use :class:`mss.MSS` instead.
    """

    def __init__(self, /, **kwargs: Any) -> None:
        # TODO(jholveck): #493 Remove compatibility constructor after 10.x transition period.
        warnings.warn(
            "mss.windows.MSS is deprecated and will be removed in 11.0; use mss.MSS instead",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)


def choose_impl(backend: str = "default", **kwargs: Any) -> MSSImplementation:
    """Return a backend-specific MSS implementation for Microsoft Windows.

    Selects and instantiates the appropriate Windows backend based on the
    ``backend`` parameter.

    :param backend: Backend selector. Valid values:

        - ``"default"`` (default): GDI-based backend using ``BitBlt`` and
          ``CreateDIBSection`` for direct memory access to pixel data.

        .. versionadded:: 10.3.0 Prior to this version, Windows had a single
            implementation selected through :class:`mss.windows.MSS`.

    :param kwargs: Additional keyword arguments passed to the backend class.
    :returns: An MSS backend implementation.

    .. versionadded:: 10.3.0 Prior to this version, this didn't exist:
          Windows had a single implementation selected through
          :class:`mss.windows.MSS`.
    """
    backend = backend.lower()
    if backend == "default":
        return MSSImplWindows(**kwargs)
    assert backend not in BACKENDS  # noqa: S101
    msg = f"Backend {backend!r} not (yet?) implemented."
    raise ScreenShotError(msg)
