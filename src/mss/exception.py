# This is part of the MSS Python's module.
# Source: https://github.com/BoboTiG/python-mss.

from __future__ import annotations

from typing import Any


class ScreenShotError(Exception):
    """Error handling class."""

    def __init__(self, message: str, /, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        #: On GNU/Linux, and if the error comes from the XServer, it contains XError details.
        #: This is an empty dict by default.
        #:
        #: For XErrors, you can find information on
        #: `Using the Default Error Handlers <https://tronche.com/gui/x/xlib/event-handling/protocol-errors/default-handlers.html>`_.
        #:
        #: .. versionadded:: 3.3.0
        self.details = details or {}
