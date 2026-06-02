# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

import warnings
from typing import Any

from mss.base import MSS


def mss(**kwargs: Any) -> MSS:
    """Create an :class:`mss.MSS` instance for the current platform.

    .. deprecated:: 10.2.0
        Use :class:`mss.MSS` directly.
    """
    # TODO(jholveck): #493 Remove compatibility deprecation path once 10.x transition period ends.
    warnings.warn(
        "mss.mss is deprecated and will be removed in a future release; use mss.MSS instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return MSS(**kwargs)
