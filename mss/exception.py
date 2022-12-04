"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""
from typing import Any, Dict


class ScreenShotError(Exception):
    """Error handling class."""

    def __init__(self, message: str, details: Dict[str, Any] = None) -> None:
        super().__init__(message)
        self.details = details or {}
