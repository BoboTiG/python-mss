"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

from __future__ import annotations

from typing import Any


class ScreenShotError(Exception):
    """Error handling class."""

    def __init__(self, message: str, /, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}
