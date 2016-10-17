from typing import Any
from .base import MSSBase


def cgfloat() -> Any: ...  # reveal_type(ctypes.c_double or ctypes.c_float) == Any
def get_infinity(maxi: bool=False) -> float: ...


class MSS(MSSBase):
    def _set_argtypes(self) -> None: ...
    def _set_restypes(self) -> None: ...
