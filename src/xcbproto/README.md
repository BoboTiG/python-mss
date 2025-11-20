# xcbproto Directory

This directory contains the tooling and protocol definitions used to generate Python bindings for XCB (X C Binding).

## Overview

- **`gen_xcb_to_py.py`**: Code generator that produces Python/ctypes bindings from XCB protocol XML files.
- **`*.xml`**: Protocol definition files vendored from the upstream [xcbproto](https://gitlab.freedesktop.org/xorg/proto/xcbproto) repository. These describe the X11 core protocol and extensions (RandR, Render, XFixes, etc.).

## Workflow

The generator is a **maintainer tool**, not part of the normal build process:

1. When the project needs new XCB requests or types, a maintainer edits the configuration in `gen_xcb_to_py.py` (see `TYPES` and `REQUESTS` dictionaries near the top).
2. The maintainer runs the generator:

   ```bash
   python src/xcbproto/gen_xcb_to_py.py
   ```

3. The generator reads the XML protocol definitions and emits `xcbgen.py`.
4. The maintainer ensures that this worked correctly, and moves the file to `src/mss/linux/xcbgen.py`.
4. The generated `xcbgen.py` is committed to version control and distributed with the package, so end users never need to run the generator.

## Protocol XML Files

The `*.xml` files are **unmodified copies** from the upstream xcbproto project. They define the wire protocol and data structures used by libxcb. Do not edit these files.

## Why Generate Code?

The XCB C library exposes thousands of protocol elements. Rather than hand-write ctypes bindings for every structure and request, we auto-generate only the subset we actually use. This keeps the codebase lean while ensuring the bindings exactly match the upstream protocol definitions.

## Dependencies

- **lxml**: Required to parse the XML protocol definitions.
- **Python 3.12+**: The generator uses modern Python features.

Note that end users do **not** need lxml; it's only required if you're regenerating the bindings.
