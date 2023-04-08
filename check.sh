#!/bin/bash
#
# Small script to ensure quality checks pass before submitting a commit/PR.
#
python -m isort docs mss
python -m black --line-length=120 docs mss
python -m flake8 docs mss
python -m pylint mss
# "--platform win32" to not fail on ctypes.windll (it does not affect the overall check on other OSes)
python -m mypy --platform win32 --exclude mss/tests mss docs/source/examples
