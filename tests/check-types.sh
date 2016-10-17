#!/usr/bin/env sh

export MYPYPATH="$(pwd)/stubs"

~/.local/bin/mypy \
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
