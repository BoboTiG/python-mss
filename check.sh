#!/bin/bash
#
# Small script to ensure quality checks pass before submitting a commit/PR.
#
python -m isort docs src
python -m black --line-length=120 docs src
python -m flake8 docs src
python -m pylint src/mss
# "--platform win32" to not fail on ctypes.windll (it does not affect the overall check on other OSes)
python -m mypy --platform win32 --exclude src/tests src docs/source/examples
