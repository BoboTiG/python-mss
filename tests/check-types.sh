#!/usr/bin/env sh

# export MYPYPATH="$(pwd)/stubs"

mypy \
    --silent-imports \
    --disallow-untyped-calls \
    --disallow-untyped-defs \
    --check-untyped-defs \
    --warn-incomplete-stub \
    --warn-redundant-casts \
    --warn-unused-ignores \
    --strict-optional \
    --scripts-are-modules \
    --show-column-numbers \
    "$@"
