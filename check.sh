#!/bin/bash
#
# Small script to ensure quality checks pass before submitting a commit/PR.
#
set -eu

python -m ruff --fix docs src
python -m ruff format docs src

# "--platform win32" to not fail on ctypes.windll (it does not affect the overall check on other OSes)
python -m mypy --platform win32 src docs/source/examples
