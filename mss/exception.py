# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""


class ScreenShotError(Exception):
    """ Error handling class. """

    def __init__(self, message, details=None):
        # type: (Dict[str, Any]) -> None
        super(Exception, self).__init__(message)
        self.details = details or dict()
