from __future__ import annotations

import gc
from ctypes import (
    POINTER,
    Structure,
    addressof,
    c_int,
    c_void_p,
    cast,
    pointer,
    sizeof,
)
from types import SimpleNamespace
from typing import Any, Callable
from unittest.mock import Mock
from weakref import finalize

import pytest

from mss.exception import ScreenShotError
from mss.linux import base, xcb, xgetimage
from mss.linux.xcbhelpers import (
    XcbExtension,
    array_from_xcb,
    depends_on,
    list_from_xcb,
)


def _force_gc() -> None:
    gc.collect()
    gc.collect()


class _Placeholder:
    """Trivial class to test weakrefs"""


def test_depends_on_defers_parent_teardown_until_child_collected() -> None:
    parent = _Placeholder()
    child = _Placeholder()
    finalizer_calls: list[str] = []
    finalize(parent, lambda: finalizer_calls.append("parent"))

    depends_on(child, parent)

    del parent
    _force_gc()
    assert finalizer_calls == []

    del child
    _force_gc()
    assert finalizer_calls == ["parent"]


def test_ctypes_scalar_finalizer_runs_when_object_collected() -> None:
    callback = Mock()

    foo = c_int(42)
    finalize(foo, callback)
    del foo
    _force_gc()

    callback.assert_called_once()


class FakeCEntry(Structure):
    _fields_ = (("value", c_int),)


class FakeParentContainer:
    def __init__(self, values: list[int]) -> None:
        self.count = len(values)
        array_type = FakeCEntry * self.count
        self.buffer = array_type(*(FakeCEntry(v) for v in values))
        self.pointer = cast(self.buffer, POINTER(FakeCEntry))


class FakeIterator:
    def __init__(self, parent: FakeParentContainer) -> None:
        self.parent = parent
        self.data = parent.pointer
        self.rem = parent.count

    @staticmethod
    def next(iterator: FakeIterator) -> None:
        iterator.rem -= 1
        if iterator.rem == 0:
            return
        current_address = addressof(iterator.data.contents)
        next_address = current_address + sizeof(FakeCEntry)
        iterator.data = cast(c_void_p(next_address), POINTER(FakeCEntry))


def test_list_from_xcb_keeps_parent_alive_until_items_drop() -> None:
    parent = FakeParentContainer([1, 2, 3])
    callback = Mock()
    finalize(parent, callback)

    items = list_from_xcb(FakeIterator, FakeIterator.next, parent)  # type: ignore[arg-type]
    assert [item.value for item in items] == [1, 2, 3]

    del parent
    _force_gc()
    callback.assert_not_called()

    item = items[0]
    assert isinstance(item, FakeCEntry)

    del items
    _force_gc()
    callback.assert_not_called()

    del item
    _force_gc()
    callback.assert_called_once()


def test_array_from_xcb_keeps_parent_alive_until_array_gone() -> None:
    parent = _Placeholder()
    callback = Mock()
    finalize(parent, callback)

    values = [FakeCEntry(1), FakeCEntry(2)]
    array_type = FakeCEntry * len(values)
    buffer = array_type(*values)

    def pointer_func(_parent: _Placeholder) -> Any:
        return cast(buffer, POINTER(FakeCEntry))

    def length_func(_parent: _Placeholder) -> int:
        return len(values)

    array = array_from_xcb(pointer_func, length_func, parent)  # type: ignore[arg-type]
    assert [entry.value for entry in array] == [1, 2]

    del parent
    _force_gc()
    callback.assert_not_called()

    item = array[0]
    assert isinstance(item, FakeCEntry)

    del array
    _force_gc()
    callback.assert_not_called()

    del item
    _force_gc()
    callback.assert_called_once()


class _VisualValidationHarness:
    """Test utility that supplies deterministic XCB setup data."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self.setup = xcb.Setup()
        self.screen = xcb.Screen()
        self.format = xcb.Format()
        self.depth = xcb.Depth()
        self.visual = xcb.Visualtype()
        self._setup_ptr = pointer(self.setup)
        self.connection = xcb.Connection()

        fake_lib = SimpleNamespace(
            xcb=SimpleNamespace(
                xcb_prefetch_extension_data=lambda *_args, **_kwargs: None,
                xcb_get_setup=lambda _conn: self._setup_ptr,
            ),
            randr_id=XcbExtension(),
            xfixes_id=XcbExtension(),
        )
        self._monkeypatch.setattr(xcb, "LIB", fake_lib)
        self._monkeypatch.setattr(xcb, "connect", lambda _display=None: (self.connection, 0))
        self._monkeypatch.setattr(xcb, "disconnect", lambda _conn: None)
        self._monkeypatch.setattr(xcb, "setup_roots", self._setup_roots)
        self._monkeypatch.setattr(xcb, "setup_pixmap_formats", self._setup_pixmap_formats)
        self._monkeypatch.setattr(xcb, "screen_allowed_depths", self._screen_allowed_depths)
        self._monkeypatch.setattr(xcb, "depth_visuals", self._depth_visuals)

        self.reset()

    def reset(self) -> None:
        self.setup.image_byte_order = xcb.ImageOrder.LSBFirst
        self.screen.root = xcb.Window(1)
        self.screen.root_depth = 32
        visual_id = 0x1234
        self.screen.root_visual = xcb.Visualid(visual_id)

        self.format.depth = self.screen.root_depth
        self.format.bits_per_pixel = base.SUPPORTED_BITS_PER_PIXEL
        self.format.scanline_pad = base.SUPPORTED_BITS_PER_PIXEL

        self.depth.depth = self.screen.root_depth

        self.visual.visual_id = xcb.Visualid(visual_id)
        self.visual.class_ = xcb.VisualClass.TrueColor
        self.visual.red_mask = base.SUPPORTED_RED_MASK
        self.visual.green_mask = base.SUPPORTED_GREEN_MASK
        self.visual.blue_mask = base.SUPPORTED_BLUE_MASK

        self.screens = [self.screen]
        self.pixmap_formats = [self.format]
        self.depths = [self.depth]
        self.visuals = [self.visual]

    def _setup_roots(self, _setup: xcb.Setup) -> list[xcb.Screen]:
        return self.screens

    def _setup_pixmap_formats(self, _setup: xcb.Setup) -> list[xcb.Format]:
        return self.pixmap_formats

    def _screen_allowed_depths(self, _screen: xcb.Screen) -> list[xcb.Depth]:
        return self.depths

    def _depth_visuals(self, _depth: xcb.Depth) -> list[xcb.Visualtype]:
        return self.visuals


@pytest.fixture
def visual_validation_env(monkeypatch: pytest.MonkeyPatch) -> _VisualValidationHarness:
    return _VisualValidationHarness(monkeypatch)


def test_xgetimage_visual_validation_accepts_default_setup(visual_validation_env: _VisualValidationHarness) -> None:
    visual_validation_env.reset()
    mss_instance = xgetimage.MSS()
    try:
        assert isinstance(mss_instance, xgetimage.MSS)
    finally:
        mss_instance.close()


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda env: setattr(env.setup, "image_byte_order", xcb.ImageOrder.MSBFirst), "LSB-First"),
        (lambda env: setattr(env.screen, "root_depth", 16), "color depth 24 or 32"),
        (lambda env: setattr(env, "pixmap_formats", []), "supported formats"),
        (lambda env: setattr(env.format, "bits_per_pixel", 16), "32 bpp"),
        (lambda env: setattr(env.format, "scanline_pad", 16), "scanline padding"),
        (lambda env: setattr(env, "depths", []), "supported depths"),
        (lambda env: setattr(env, "visuals", []), "supported visuals"),
        (lambda env: setattr(env.visual, "class_", xcb.VisualClass.StaticGray), "TrueColor"),
        (lambda env: setattr(env.visual, "red_mask", 0), "BGRx ordering"),
    ],
)
def test_xgetimage_visual_validation_failures(
    visual_validation_env: _VisualValidationHarness,
    mutator: Callable[[_VisualValidationHarness], None],
    message: str,
) -> None:
    mutator(visual_validation_env)
    with pytest.raises(ScreenShotError, match=message):
        xgetimage.MSS()
