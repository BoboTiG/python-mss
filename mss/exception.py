"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Dict  # noqa


class ScreenShotError(Exception):
    """ Error handling class. """

    def __init__(self, message, details=None):
        # type: (str, Dict[str, Any]) -> None
        super().__init__(message)
        self.details = details or {}
