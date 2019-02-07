# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss
"""

import collections
from typing import Dict, List, Tuple


Monitor = Dict[str, int]
Monitors = List[Monitor]

Pixel = Tuple[int, int, int]
Pixels = List[Pixel]

Pos = collections.namedtuple("Pos", "left, top")
Size = collections.namedtuple("Size", "width, height")
