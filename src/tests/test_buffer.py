"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.
"""

import gc

import pytest

from mss.buffer import FAST_PATH_AVAILABLE, _FinalizingBufferIntermediate, finalizing_buffer


def test_finalizer_runs_once() -> None:
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    wrapped = finalizing_buffer(bytearray(b"abcd"), finalizer)
    assert finalizer_calls == (0 if FAST_PATH_AVAILABLE else 1)

    del wrapped
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.parametrize(
    ("buffer_class", "readonly"),
    [
        (bytearray, False),
        (bytes, True),  # type: ignore[list-item]
    ],
)
def test_finalizing_buffer_preserves_readonly(buffer_class: type, readonly: bool) -> None:
    base_buffer = buffer_class(b"abcd")
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    view = finalizing_buffer(base_buffer, finalizer)
    assert finalizer_calls == (0 if FAST_PATH_AVAILABLE else 1)
    assert isinstance(view, memoryview)
    assert view.readonly == readonly

    view.release()
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(FAST_PATH_AVAILABLE, reason="Covers behavior only present prior to Python 3.12")
def test_finalizing_buffer_slow_path() -> None:
    data = bytearray(b"abcd")
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    wrapped = finalizing_buffer(data, finalizer)
    assert finalizer_calls == 1

    # Ensure that it made a copy
    data[0] = ord("Z")
    assert wrapped.tobytes() == b"abcd"
    wrapped[1] = ord("Y")
    assert data == bytearray(b"Zbcd")

    wrapped.release()
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(not FAST_PATH_AVAILABLE, reason="Covers behavior only present in Python 3.12+")
def test_finalizing_buffer_fast_path_is_zero_copy() -> None:
    data = bytearray(b"abcd")
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    wrapped = finalizing_buffer(data, finalizer)
    assert finalizer_calls == 0

    data[0] = ord("Z")
    assert wrapped[0] == ord("Z")
    wrapped[1] = ord("Y")
    assert data[1] == ord("Y")

    wrapped.release()
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(not FAST_PATH_AVAILABLE, reason="Covers behavior only present in Python 3.12+")
def test_memoryview_release() -> None:
    """Releasing a memoryview releases the buffer immediately

    CPython special-cases a memoryview of a memoryview (and
    finalizing_buffer returns a memoryview), so we test it specially.
    """
    data = bytearray(b"abcdefgh")
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    base = finalizing_buffer(data, finalizer)
    child = memoryview(base)

    del base
    gc.collect()
    assert finalizer_calls == 0

    child.release()
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(not FAST_PATH_AVAILABLE, reason="Covers behavior only present in Python 3.12+")
def test_memoryview_del() -> None:
    """Garbage-collecting a memoryview releases the buffer immediately

    CPython special-cases a memoryview of a memoryview (and
    finalizing_buffer returns a memoryview), so we test it specially.
    """
    data = bytearray(b"abcdefgh")
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    base = finalizing_buffer(data, finalizer)
    child = memoryview(base)

    del base
    gc.collect()
    assert finalizer_calls == 0

    del child
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(not FAST_PATH_AVAILABLE, reason="Covers behavior only present in Python 3.12+")
def test_tree() -> None:
    """A complex tree retains a single buffer until it's completely gone"""
    # These imports are here instead of at the top, since we only install Pillow and NumPy on Python 3.12 and later.
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    # Since we're using Pillow as one stage, we need something image-like: here, a rectangle of a pleasing green color.
    data = bytearray(b"\x76\xb9\x00\xff" * (320 * 200))
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    # Set up a tree of derived buffers of different types:
    # base
    #  \- array
    #      \- mv
    #      \- array_shaped
    #           \- img
    base = finalizing_buffer(data, finalizer)
    array = np.frombuffer(base, dtype=np.uint8)
    array_shaped = array.reshape((320, 200, 4))
    mv = memoryview(array)
    img = Image.frombuffer("RGBA", (320, 200), array_shaped, "raw", "RGBA", 0, 1)

    # Ensure that the tree is zero-copy.
    data[0] = 42
    assert img.getpixel((0, 0)) == (42, 0xB9, 0, 0xFF)

    # Ensure that if we delete much of the tree, the buffer still is retained.
    del base
    del array
    del img
    mv.release()  # We explicitly call release, to test its path too, but just del would suffice.
    del mv
    gc.collect()
    assert finalizer_calls == 0

    # Now, it all gets released when we delete the last reference to the buffer.
    del array_shaped
    gc.collect()
    assert finalizer_calls == 1


@pytest.mark.skipif(not FAST_PATH_AVAILABLE, reason="Covers behavior only present in Python 3.12+")
def test_intermediate_enforces_single_use() -> None:
    """Trying to reuse a _FinalizingBufferIntermediate asserts out."""
    finalizer_calls = 0

    def finalizer() -> None:
        nonlocal finalizer_calls
        finalizer_calls += 1

    intermediate = _FinalizingBufferIntermediate(bytearray(b"abcd"), finalizer)

    view = intermediate.__buffer__(0)  # 0: PyBUF_SIMPLE
    assert view.tobytes() == b"abcd"

    with pytest.raises(AssertionError, match="Buffer can only be requested once"):
        intermediate.__buffer__(0)

    intermediate.__release_buffer__(view)
    assert finalizer_calls == 1

    with pytest.raises(AssertionError, match="Buffer can only be released once"):
        intermediate.__release_buffer__(view)

    with pytest.raises(AssertionError, match="Buffer can only be requested once"):
        intermediate.__buffer__(0)

    assert finalizer_calls == 1
