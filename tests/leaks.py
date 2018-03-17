# coding: utf-8
"""
python3 -m memory_profiler tests/leaks.py
"""
from memory_profiler import profile

from mss import mss


@profile
def check_instance():
    for _ in range(100):
        with mss() as sct:
            sct.shot()


@profile
def check_calls():
    with mss() as sct:
        for _ in range(100):
            sct.shot()


check_instance()
check_calls()
