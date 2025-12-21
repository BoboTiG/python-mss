#! /usr/bin/env python3

"""Stream to a TinyTV <https://tinytv.us/>

A TinyTV is a roughly 5cm tall TV with a 2cm screen.  It can play
videos from built-in storage, or a computer can stream video to it.

This program will capture your display, and stream it to the TinyTV.

While streaming is supported with the TinyTV 2, Mini, and DIY Kit,
this has only been tested with the TinyTV 2.  Reports regarding tests
with other devices are welcome!

The firmware code in the TinyTV that we're talking to is at
https://github.com/TinyCircuits/TinyCircuits-TinyTVs-Firmware/blob/master/USB_CDC.h

In short, the TinyTV takes its input as Motion JPEG (MJPG), a simple
sequence of frames, each encoded as a single JPEG file.  With JPEG, it
is difficult to tell where one JPEG image ends and the next begins.
So, each frame is preceded by a delimiter: this is the JSON text
{"FRAME":1234}, where the number is the size in bytes.  This is
followed by the JPEG data itself.

How fast can it be?  The time it takes for the TinyTV to process the
JPEG seems to be the main bottleneck.  In our test, the official
streamer at https://tinytv.us/Streaming/ gets about 15 fps for a 4k
capture, which is about the same as the non-threaded simple demo gets
(depending on the screen contents).

We use a background sending thread so that we can prepare one
screenshot while the other is being sent.  That lets us get about
20-30 fps for 4k in our tests, which seems to be close to the limit of
the TinyTV hardware (again, depending on the JPEG settings and screen
contents).

Before connecting, we can't distinguish between a TinyTV and any other
Raspberry Pi Pico by USB IDs alone.  You may need to use the --device
or --usb-serial-number flag to tell the program which serial device to
use.  Different OSs have different ways to identify the correct
device.

Windows:

On Windows, the serial device will be something like COM3.  You can
find the correct port by looking in Device Manager under "Ports (COM &
LPT)".  You can specify the device to use with the --device flag.

You may want to use the --list-devices flag to identify the correct
device, and use the --usb-serial-number flag in future invocations.
This is because Windows COM port assignments can change between
reboots or replugging the device.

macOS:

On macOS, the serial device is usually something like
/dev/tty.usbserial-1234ABCD or /dev/tty.usbmodem1234ABCD, where
1234ABCD is a device-specific value that will be the same every time
that device is plugged in.  You can use the --device flag to point to
these.

Linux:

On Linux, the serial device is usually something like /dev/ttyACM0 or
/dev/ttyUSB0.  You can use the --device flag to point to the symlink
that is automatically created, e.g.,
/dev/serial/by-id/usb-Raspberry_Pi_Pico_0123456789ABCDEF-if00.

You need write access to the serial device that represents the TinyTV.
If you run this program as a normal user, you may need to set up a
udev rule to give your user access.

You can do this by creating a file named
/etc/udev/rules.d/70-tinytv.rules or something similar.  Name it with
a number below 73 so it runs before 73-seat-late.rules (where uaccess
is applied).  (Note that this rule will be applied to many Raspberry
Pi Pico devices; you can add a ATTRS{serial} test to limit it to just
your TinyTV.)

    # TinyTV2, TinyTVKit
    SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{idProduct}=="0003|000a", TAG+="uaccess"
    # TinyTVMini
    SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="8009", TAG+="uaccess"

Once you have the rule in place, reload udev rules:

    sudo udevadm control --reload-rules

Then unplug and replug your TinyTV.
"""

# I see you're the type of person who likes to read the source code, instead of just the documentation.  Maybe you're
# looking here because you're getting ideas about doing something similar in your own projects, or maybe you're just
# curious about how this works.  Terrific!  Glad to have you with us!
#
# You may want to read the simple demo first, to get an idea of what we're doing here.  This program follows the same
# basic steps, but we organize them into a multithreaded pipeline for higher performance.  We also add more
# configuration options and things like that.
#
# Still, the basic flow is still straightforward:
#     Capture from MSS -> Scale and JPEG-encode in PIL -> Send to serial port
#
# The core idea behind this program is a pipeline: instead of fully processing one video frame at a time, we work on
# several different frames at once, each at a different stage of processing.
#
# At any given moment, one frame might be getting captured, the previous frame might be getting scaled and
# JPEG-encoded, and an even earlier frame might be in the process of being sent to the TinyTV.
#
# The stages are:
#
# * capture a screenshot (MSS)
# * scale and JPEG-encode it (Pillow)
# * send it to the TinyTV (serial)
#
# Between each stage is a mailbox.  A mailbox can hold one item.  A stage puts its output into the next mailbox, and
# the following stage takes it when it's ready.
#
# If a stage tries to read from an empty mailbox, it waits.  If it tries to write to a full mailbox, it also waits.
#
# This lets the stages overlap. While one frame is being sent to the TinyTV (the slowest step), the next frame can
# already be captured or encoded.
#
# Eventually, the slowest stage determines the overall speed.  When that happens, earlier stages naturally stop and
# wait.  This is called backpressure: work piles up behind the bottleneck instead of running ahead and wasting effort.
#
# The result is that the TinyTV may show a frame that's a few frames behind what's currently on your screen. That
# latency is the cost of keeping the pipeline efficient.
#
# An alternative design would be to drop old frames when a mailbox is full, so the display stays closer to "live".
# That reduces lag, but it means capturing and encoding frames that are never shown.  Which approach is better depends
# on your goals; this program chooses to block and apply backpressure.

from __future__ import annotations

import argparse
import contextlib
import functools
import io
import itertools
import logging
import os
import re
import sys
import time
from collections import deque
from collections.abc import Generator, Iterable, Iterator
from threading import Condition, Lock, Thread
from typing import TYPE_CHECKING, Generic, Literal, TypeVar, overload

import serial
from PIL import Image, ImageOps
from prettytable import PrettyTable, TableStyle
from serial.tools import list_ports

import mss

if TYPE_CHECKING:
    from collections.abc import Callable

# The keys in this are substrings in the tvType query.  Make sure that they're all distinct: having both "TinyTV2" and
# "TinyTV2.1" in here would mean that a 2.1 might be misidentified as a 2.  We use substrings instead of parsing the
# response because the TinyTV currently responds with invalid JSON, and they might change that later.
SUPPORTED_DEVICES = {
    # Only the TinyTV2 kit has been tested.  Reports with other hardware are welcome!
    b"TinyTV2": {
        # Uses an RP2040 board.  2e8a:000a is the ID when it's in normal mode (not recovery), which is the default
        # VID:PID for an RP2040.
        "usb_id": (0x2E8A, 0x000A),
        "size": (210, 135),
    },
    b"TinyTVKit": {
        # Uses an RP2040 board, like the TinyTV2.  I assume it also uses the default VID:PID.
        "usb_id": (0x2E8A, 0x000A),
        "size": (96, 64),
    },
    b"TinyTVMini": {
        # Uses a board based on the SAMD21, similar to an Arduino Zero.  From what I see in the TinyCircuits Arduino
        # board file, it enumerates as 03eb:8009.  I think it uses 03eb:8008 in recovery mode.
        "usb_id": (0x03EB, 0x8009),
        "size": (64, 64),
    },
}

# Downscaling is one of the most time-intensive steps, and the practical difference between the high-quality
# algorithms isn't going to be perceptible in this context.
SCALING_ALGORITHM = Image.Resampling.HAMMING

# When choosing JPEG quality, note that higher quality images are slower for the TinyTV to decode; you can get a few
# extra FPS by lowering the quality to something like 35.  However, with some content (like text windows, which the
# user will have on their screen when they first start this program), heavy compression makes JPEG artifacts really
# visible.  You just don't want to see that on your TinyTV.
DEFAULT_JPEG_QUALITY = 75


T = TypeVar("T")
U = TypeVar("U")

LOGGER = logging.getLogger("tinytv-stream")


class MailboxShutDown(Exception):  # noqa: N818 (An exception, but not an error)
    """Exception to indicate that a Mailbox has been shut down.

    This will be raised if Mailbox.get() or Mailbox.put() is run on a
    mailbox after its .shutdown() method has been called, or if it is
    called while waiting.
    """

    def __init__(self, mailbox: Mailbox) -> None:
        #: The mailbox that was shut down
        self.mailbox = mailbox

    def __str__(self) -> str:
        return f"Mailbox shut down: {self.mailbox}"


class Mailbox(Generic[T]):
    """Thread-safe container to pass a single object at a time between threads.

    A Mailbox can be shut down to indicate that it is no longer
    available.  This can be used by a producer to indicate that no
    more items will be forthcoming, or by a consumer to indicate that
    it is no longer able to accept more objects.

    In Python 3.13, this has the same basic functionality as
    queue.Queue(1).  Prior to 3.13, there was no
    queue.Queue.shutdown() method.  The mechanisms for using mailboxes
    as iterables, or adding items from iterables, are also not part of
    queue.Queue in any version of Python.
    """

    def __init__(self) -> None:
        #: Lock to protect mailbox state
        self.lock = Lock()
        self._condition = Condition(lock=self.lock)
        #: Indicates whether an item is present in the mailbox
        self.has_item = False
        self._item: T | None = None
        #: Indicates whether the mailbox has been shut down
        self.is_shutdown = False

    def get(self) -> T:
        """Return and remove the item being held by the mailbox.

        If an item is not presently available, block until another
        thread calls .put().
        """
        with self._condition:
            while True:
                # We test to see if an item is present before testing if the queue is shut down.  This is so that a
                # non-immediate shutdown allows the mailbox to be drained.
                if self.has_item:
                    rv = self._item
                    self._item = None  # Don't hold an unnecessary reference
                    self.has_item = False
                    self._condition.notify_all()
                    return rv  # type:ignore[return-value]
                if self.is_shutdown:
                    raise MailboxShutDown(self)
                self._condition.wait()

    def get_many(self) -> Iterable[T]:
        """Yield items as they appear in the mailbox.

        The iterator exits the mailbox is shut down; MailboxShutDown
        is not raised into the caller.
        """
        return iter(self)

    def put(self, item: T) -> None:
        """Store an item in the mailbox.

        If an item is already in the mailbox, block until another
        thread calls .get().
        """
        with self._condition:
            while True:
                if self.is_shutdown:
                    raise MailboxShutDown(self)
                if not self.has_item:
                    self._item = item
                    self.has_item = True
                    self._condition.notify()
                    return
                self._condition.wait()

    def put_many(self, items: Iterable[T]) -> Iterator[T]:
        """Put the elements of iterable in the mailbox, one at a time.

        If the mailbox is shut down before all the elements can be put
        into it, a MailboxShutDown exception is _not_ raised.

        Returns an iterator containing any remaining items, including
        the one that was being processed when the mailbox was shut
        down.  The first item (if any) of this iterator can be
        immediately accessed with next; subsequent items defer to the
        input iterable, so may block.
        """
        iterator = iter(items)
        for item in iterator:
            # We put this try/except inside the for loop, to make sure we don't accidentally filter out an exception
            # that escaped the items iterator.
            try:
                self.put(item)
            except MailboxShutDown:
                return itertools.chain([item], iterator)
            # Remove references to the value once it's not needed.  This lets objects with advanced buffer semantics
            # reclaim the object's memory immediately, without waiting for the next iteration of the iterable.
            del item
        return iter([])

    def shutdown(self, *, immediate: bool = False) -> None:
        """Shut down the mailbox, marking it as unavailable for future use.

        Any callers currently blocked in .get or .put, or any future
        caller to those methods, will recieve a MailboxShutDown
        exception.  Callers using .get_many or iterating over the
        mailbox will see the iteration end.  Callers to .put_many will
        stop adding items.

        If immediate is False (the default), and an item is currently
        in the mailbox, it will be returned by the next call to
        .get(), and the one after that will raise MailboxShutDown.

        It is safe to call this method multiple times, including to
        promote a non-immediate shutdown to an immediate one.
        """
        with self._condition:
            # We don't actually need to check whether we've been called already.
            self.is_shutdown = True
            if immediate:
                self._item = None
                self.has_item = False
            self._condition.notify_all()

    def __iter__(self) -> Iterator[T]:
        """Yield items as they appear in the mailbox.

        The iterator exits when the mailbox is shut down;
        MailboxShutDown is not raised into the caller.
        """
        with contextlib.suppress(MailboxShutDown):
            while True:
                yield self.get()


class PipelineStage(Thread, Generic[T, U]):
    """A stage of a multi-threaded pipeline.

    The target function will be called once, and should yield one
    value for each element.

    If an in_mailbox is provided, the function will get an iterable of
    its successive elements.  If an out_mailbox is provided, it will
    be supplied with the successive outputs of the target function.

    If the either mailbox is shut down, the target function's loop
    will stop being called.  Both mailboxes will be shut down when the
    target function ends.

    Note to readers adapting this class to their own programs:

    This is designed for linear pipelines: it is not meant to support
    fan-in (multiple stages feeding one mailbox) or fan-out (one
    mailbox feeding multiple stages).  The shutdown semantics of these
    sorts of pipelines will depend heavily on what it's used for, and
    this demo only needs a simple pipeline.
    """

    # Source stage
    @overload
    def __init__(
        self,
        target: Callable[[], Generator[U]],
        *,
        out_mailbox: Mailbox[U],
        name: str | None = None,
    ) -> None: ...

    # Transformer stage
    @overload
    def __init__(
        self,
        target: Callable[[Iterable[T]], Generator[U]],
        *,
        in_mailbox: Mailbox[T],
        out_mailbox: Mailbox[U],
        name: str | None = None,
    ) -> None: ...

    # Sink stage
    @overload
    def __init__(
        self,
        target: Callable[[Iterable[T]], None],
        *,
        in_mailbox: Mailbox[T],
        name: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        target: Callable[[], Generator[U]] | Callable[[Iterable[T]], Generator[U]] | Callable[[Iterable[T]], None],
        *,
        in_mailbox: Mailbox[T] | None = None,
        out_mailbox: Mailbox[U] | None = None,
        name: str | None = None,
    ) -> None:
        """Initialize the PipelineStage.

        Either :param:`in_mailbox` or :param:`out_mailbox` is
        required.  Otherwise, it would be a pipeline stage that can't
        connect to anything else.  (You can always use
        :class:`threading.Thread` directly if you need that behavior.)

        :param target: Function to run during the stage.  This will be
            called once, in a separate thread.  This should take one
            argument if :param:`in_mailbox` is provided, or no
            arguments otherwise.  If you want additional arguments
            (such as configuration), use :func:`functools.partial`.
        :param in_mailbox: An optional :class:`Mailbox` to provide
            inputs to the target function.  The target function will
            be called with one argument, an iterable that you can use
            in a for loop or similar construct, to get the successive
            values.
        :param out_mailbox: An optional :class:`Mailbox` to receive
            outputs from the target function.  If this is provided,
            the target function must be a generator (a function that
            uses ``yield`` instead of ``return``).  The successive
            outputs from the function will be placed in
            :param:`out_mailbox`.
        :param name: An optional name for debugging purposes; see
            :attr:`threading.Thread.name`.
        """
        if in_mailbox is None and out_mailbox is None:
            msg = "Cannot have a pipeline stage with neither inputs nor outputs"
            raise ValueError(msg)
        self.in_mailbox = in_mailbox
        self.out_mailbox = out_mailbox
        self.target = target
        #: The exception (if any) raised by the target function
        self.exc: Exception | None = None
        super().__init__(name=name, daemon=True)

    def run(self) -> None:
        """Execute the pipeline stage.

        This should not be run directly.  Instead, use the start()
        method (inherited from threading.Thread) to run this in a
        background thread.

        This will run the target function, managing input and output
        mailboxes.  When the stage completes, whether normally or with
        an error, the mailboxes will be shut down.
        """
        try:
            if self.out_mailbox is None:
                # This is a sink function, the easiest to deal with.  Since a mailbox is iterable, we can just pass it
                # to the target function.
                assert self.in_mailbox is not None  # noqa: S101
                self.target(self.in_mailbox)  # type:ignore[call-arg]
                return
            # This is a source or transformation function.
            out_iterable = self.target() if self.in_mailbox is None else self.target(self.in_mailbox)  # type:ignore[call-arg]
            if not isinstance(out_iterable, Generator):
                msg = (
                    "Pipeline target function was expected to be a generator; "
                    f"instead, it returned a {type(out_iterable)}."
                )
                raise TypeError(msg)  # noqa: TRY301
            # Once a generator is closed, the yield call (where they block when they send an object downstream) will
            # raise GeneratorExit.  That lets finally: blocks, with: exits, etc. run.  This happens automatically when
            # out_iterable is garbage-collected.  We still close it explicitly to so it gets the GeneratorExit, in case
            # something (like an exception object) is holding a reference to out_iterable.
            with contextlib.closing(out_iterable):
                self.out_mailbox.put_many(out_iterable)
        except Exception as e:
            # We store the exception, so that our caller can choose what to do about it after they call join.
            self.exc = e
            raise
        finally:
            if self.in_mailbox is not None:
                self.in_mailbox.shutdown()
            if self.out_mailbox is not None:
                self.out_mailbox.shutdown()

    def __str__(self) -> str:
        return f"<PipelineStage {self.name} running={self.is_alive()} thread_id={self.native_id}>"


def list_devices() -> None:
    """Display all USB serial ports in a formatted table."""
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return

    # Create and populate table
    table = PrettyTable(["Device", "USB ID", "Serial Number", "Manufacturer", "Product", "Description"])
    table.align = "l"
    table.set_style(TableStyle.PLAIN_COLUMNS)
    table.sortby = "Device"
    for port in ports:
        usb_id = f"{port.vid:04x}:{port.pid:04x}".lower() if port.vid and port.pid else ""
        serial_num = port.serial_number or ""
        table.add_row(
            [
                port.device,
                usb_id,
                serial_num,
                port.manufacturer or "",
                port.product or "",
                port.description if port.description and port.description != "n/a" else "",
            ]
        )

    print(table)


def get_device_name(usb_id: str | None, usb_serial_number: str | None) -> str:  # noqa: PLR0912
    """Find the device name for a USB serial port.

    If multiple serial ports match the criteria, an exception is
    raised.

    We currently don't provide the user a way to select an interface
    if the device has multiple USB endpoints.  The TinyTV doesn't do
    that, so it's not urgent.

    :param usb_id: USB vendor:product ID in format "vvvv:pppp".
    :param usb_serial_number: Optional USB serial number to filter by.
    :returns: The device name (e.g., "/dev/ttyACM0" on Linux or "COM3"
        on Windows).
    """
    if usb_id is not None:
        vendor_str, product_str = usb_id.lower().split(":", maxsplit=1)
        vendor = int(vendor_str, 16)
        product = int(product_str, 16)

    candidates = []

    # We sort the ports by name so that the --verbose output is nicer to read.
    for port in sorted(list_ports.comports(), key=lambda port: port.name):
        if port.vid is None or port.pid is None:
            LOGGER.debug("%s: device is not USB", port.name)
            continue
        if usb_serial_number is not None and port.serial_number != usb_serial_number:
            LOGGER.debug("%s: serial number does not match (found %r)", port.name, port.serial_number)
            continue
        if usb_id is not None:
            if (port.vid, port.pid) == (vendor, product):
                LOGGER.debug("%s: device matches")
                candidates.append(port)
            else:
                LOGGER.debug("%s: USB id mismatch: %04x:%04x", port.name, port.vid, port.pid)
        else:
            for device_name, device_spec in SUPPORTED_DEVICES.items():
                if (port.vid, port.pid) == device_spec["usb_id"]:
                    LOGGER.debug(
                        "%s: USB id matches %s: %04x:%04x", port.name, device_name.decode("ascii"), port.vid, port.pid
                    )
                    candidates.append(port)
                    break
            else:
                LOGGER.debug("%s: USB id not in supported device list: %04x:%04x", port.name, port.vid, port.pid)

    if len(candidates) == 1:
        # We've been logging the name attribute, which is the human-friendly name: "ttyACM0".  We return the device
        # attribute, which is the full path: "/dev/ttyACM0".
        return candidates[0].device

    msg = "Cannot find USB device" if len(candidates) == 0 else "Multiple USB devices found"
    if usb_id is not None:
        msg += f": {usb_id}"
    else:
        msg += " in supported device list"
    if usb_serial_number is not None:
        msg += f" with serial number {usb_serial_number}"
    if len(candidates) != 0:
        msg += f": {', '.join(c.name for c in candidates)}"

    msg += "\nHint: Consider --list-devices, find your device, and use the --device flag."

    raise RuntimeError(msg)


def get_screen_size(ser: serial.Serial) -> tuple[int, int]:
    """Identify the TinyTV type and screen size.

    :param ser: An open serial connection to the TinyTV.
    :return: The screen size as (width, height).
    """
    # First, clear out any remaining junk in the buffer, such as from earlier buggy runs.
    while ser.in_waiting:
        ser.reset_input_buffer()
    # Check for the device type.
    LOGGER.debug('>>> {"GET":"tvType"}')
    ser.write(b'{"GET":"tvType"}')
    response = ser.readline()  # {"tvType":TinyTV2}\r\n
    LOGGER.debug("<<< %s", response.decode(errors="replace").rstrip())
    # Do a very simple check: the return format might change (such as to add quotes around the value).
    for name, spec in SUPPORTED_DEVICES.items():
        if name in response:
            LOGGER.debug("Device detected as %s", name.decode())
            return spec["size"]
    msg = f"Device is not a supported TinyTV: {ser.name}"
    raise RuntimeError(msg)


def _scale_letterbox(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Fit image to size, preserving aspect ratio, with black padding."""
    img.thumbnail(size, SCALING_ALGORITHM)
    return ImageOps.pad(img, size, color="black")


def _scale_crop(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Crop image to fit size, preserving aspect ratio."""
    return ImageOps.fit(img, size, SCALING_ALGORITHM)


def _scale_stretch(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Stretch image to exactly fit size, ignoring aspect ratio."""
    return img.resize(size, SCALING_ALGORITHM)


def capture_image(
    *,
    monitor: int | None = None,
    capture_area: dict[str, int] | None = None,
) -> Generator[Image.Image]:
    """Continuously capture images from the specified monitor.

    Either monitor or capture_area must be used, but not both.

    :param monitor: Monitor number to capture from, using the standard
        MSS convention (all screens=0, first screen=1, etc.).
    :param capture_area: Capture rectangle dict with 'left', 'top',
        'width', 'height'.
    :yields: PIL Image objects from the captured monitor.
    """
    with mss.mss() as sct:
        rect = capture_area if capture_area is not None else sct.monitors[monitor]
        LOGGER.debug("Capture area: %i,%i, %ix%i", rect["left"], rect["top"], rect["width"], rect["height"])

        while True:
            sct_img = sct.grab(rect)
            pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            yield pil_img


def process_and_encode_image(
    images: Iterable[Image.Image],
    *,
    size: tuple[int, int],
    scaling_mode: Literal["letterbox", "crop", "stretch"] = "stretch",
    quality: int = DEFAULT_JPEG_QUALITY,
) -> Generator[bytes]:
    """Scale and JPEG-encode images for TinyTV display.

    :param images: Iterable of PIL Image objects to process.
    :param size: Tuple (width, height) to resize images to.
    :param scaling_mode: How to scale images ("letterbox", "crop", or
        "stretch").
    :param quality: JPEG quality level (1-100).  Higher quality
        provides clearer images, but also is slower for the TinyTV to
        process.
    :yields: JPEG-encoded image data as bytes.
    """
    # Select the scaling function based on mode.
    scale_func = {
        "letterbox": _scale_letterbox,
        "crop": _scale_crop,
        "stretch": _scale_stretch,
    }[scaling_mode]

    for img in images:
        # Scaling large images can be slow.  To speed it up, reduce to ~3x target size before invoking the
        # high-quality scaling function.
        reduced_size = tuple(d * 3 for d in size)
        reduction_factor = max(1, img.width // reduced_size[0], img.height // reduced_size[1])
        scaled_img = img.reduce(reduction_factor)
        scaled_img = scale_func(scaled_img, size)

        with io.BytesIO() as fh:
            scaled_img.save(fh, format="JPEG", quality=quality)
            jpeg_bytes = fh.getvalue()

        yield jpeg_bytes


def send_jpeg(ser: serial.Serial, jpeg_bytes_inputs: Iterable[bytes]) -> Generator[int]:
    """Send JPEG frames to TinyTV over its USB serial connection.

    :param ser: Serial device for an open and verified connection.
    :param jpeg_bytes_inputs: Iterable of JPEG-encoded image data.  Each
        element should represent a single, self-contained image frame.
    :yields: Byte count sent for each frame (delimiter + JPEG data).
    """
    for jpeg_bytes in jpeg_bytes_inputs:
        # The TinyTV doesn't have an unambiguous error protocol: it just prints an English string.  Fortunately, it
        # doesn't print anything during normal operation.  Debug builds of the firmware can, but if you're using a
        # debug build, you know enough to adapt this code to your needs.
        if ser.in_waiting:
            # Configure a one-second timeout on the serial device, so that it will stop reading after that time,
            # instead of waiting for a full 4k of error messages.
            ser.timeout = 1
            incoming_data = ser.read(4096)
            msg = f"Error from TinyTV: {incoming_data!r}"
            raise RuntimeError(msg)

        delimiter = ('{"FRAME":%s}' % len(jpeg_bytes)).encode("ascii")  # noqa: UP031
        ser.write(delimiter)
        ser.write(jpeg_bytes)
        yield (len(delimiter) + len(jpeg_bytes))


def show_stats(byte_counts: Iterable[int]) -> None:
    """Display streaming statistics (FPS and throughput).

    Statistics are displayed over a 100-frame sliding window, which is
    about four seconds.

    FPS indicates how fast the entire pipeline can run as a whole, not
    any individual stage.

    Bps, or bytes per second, is the speed at which we are sending
    data to the TinyTV.  The TinyTV is usually the slowest part of the
    pipeline, but not because of the raw transfer speed.  If you try
    different --quality values, you'll see that at higher quality, the
    Bps goes up, but the overall FPS drops.  This indicates that the
    per-frame decoding in the TinyTV, rather than the raw transfer
    speed, is the limiting factor.

    This is run on the main thread.  This is partly a matter of
    convenience, and partly because it simplifies waiting for the
    pipeline to complete.

    :param byte_counts: Iterable of byte counts per frame.
    """
    start_time = time.clock_gettime(time.CLOCK_MONOTONIC)
    time_deque: deque[float] = deque(maxlen=100)
    byte_count_deque: deque[int] = deque(maxlen=100)
    next_display_update = 0.0
    last_status_len = 0
    for frame_count, byte_count in enumerate(byte_counts):
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        time_deque.append(now)
        byte_count_deque.append(byte_count)
        if now >= next_display_update and len(time_deque) > 1:
            next_display_update = now + 0.1
            running_time = now - start_time
            running_minutes = int(running_time / 60)
            running_seconds = int(running_time % 60)
            window_secs = time_deque[-1] - time_deque[0]
            window_frames = len(time_deque)
            window_bytes = sum(byte_count_deque)
            fps = window_frames / window_secs
            bytes_per_sec = int(window_bytes / window_secs)
            line = (
                f"{running_minutes:02d}:{running_seconds:02d} frame {frame_count}: {fps:.2f} fps, {bytes_per_sec} Bps"
            )
            this_status_len = len(line)
            full_line = f"\r{line}{' ' * (last_status_len - this_status_len)}"
            print(full_line, end="")
            last_status_len = this_status_len


def _usb_id_type(value: str) -> str:
    """Validate and return a USB ID in vvvv:pppp format.

    This is used to tell argparse how to validate the string given on
    the command line.

    :param value: The USB ID string to validate.
    :returns: The validated USB ID string.
    :raises argparse.ArgumentTypeError: If the format is invalid.
    """
    # Expect vvvv:pppp using hex digits
    if re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{4}", value):
        return value
    msg = "Invalid USB ID format; expected vvvv:pppp (hex)"
    raise argparse.ArgumentTypeError(msg)


def _quality_type(value: str) -> int:
    """Validate and return a JPEG quality value (1-100).

    This is used to tell argparse how to validate the string given on
    the command line.

    :param value: The quality value string to validate.
    :returns: The validated quality value as an integer.
    :raises argparse.ArgumentTypeError: If the value is not between 1
        and 100.
    """
    try:
        q = int(value)
    except ValueError:
        msg = "Quality must be an integer between 1 and 100"
        raise argparse.ArgumentTypeError(msg) from None
    if 1 <= q <= 100:  # noqa: PLR2004
        return q
    msg = "Quality must be between 1 and 100"
    raise argparse.ArgumentTypeError(msg)


def _capture_area_type(value: str) -> dict[str, int]:
    """Validate and return a capture area dict.

    Expected format is ``left,top,width,height`` where all values are
    integers.

    :param value: The capture area string to validate.
    :returns: Dict with 'left', 'top', 'width', 'height' keys.
    :raises argparse.ArgumentTypeError: If the format is invalid or extents
        are non-positive.
    """
    parts = value.split(",")
    if len(parts) != 4:  # noqa: PLR2004
        msg = "Capture area must have four comma-separated integers: left,top,width,height"
        raise argparse.ArgumentTypeError(msg)

    try:
        left, top, width, height = (int(part) for part in parts)
    except ValueError:
        msg = "Capture area values must be integers"
        raise argparse.ArgumentTypeError(msg) from None

    if width <= 0 or height <= 0:
        msg = "Capture area width and height must be positive"
        raise argparse.ArgumentTypeError(msg)

    return {"left": left, "top": top, "width": width, "height": height}


def main() -> None:
    """Main entry point for the TinyTV streaming application.

    Parses command-line arguments, sets up the streaming pipeline, and
    runs the capture-process-send stages in parallel threads.
    """
    parser = argparse.ArgumentParser(
        description="Stream your display to a TinyTV",
        usage="""
%(prog)s --list-devices
%(prog)s
    [ [ --usb-id VID:PID ] [ --usb-serial-number SERIAL ] | --device DEVICE ]
    [ --monitor MONITOR_NUMBER | --capture-area X,Y,R,B ]
    [ --scaling-mode {letterbox,crop,stretch} ] [ --quality QUALITY ]
""".strip(),
    )
    parser.add_argument(
        "-L",
        "--list-devices",
        action="store_true",
        help="List all USB serial ports and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Report additional details",
    )
    parser.add_argument(
        "-U",
        "--usb-id",
        type=_usb_id_type,
        help="USB VID:PID to search for (default 2e8a:000a)",
    )
    parser.add_argument(
        "-S",
        "--usb-serial-number",
        help="Match device by USB serial number instead of VID:PID",
    )
    sample_device = (
        "COM3"
        if os.name == "nt"
        else "/dev/serial/by-id/usb-Raspberry_Pi_Pico_0123456789ABCDEF-if00"
        if os.name == "posix"
        else None
    )
    sample_device_desc = f" (e.g., {sample_device})" if sample_device else ""
    parser.add_argument(
        "-d",
        "--device",
        help=(f"Serial device{sample_device_desc}"),
    )
    monitor_group = parser.add_mutually_exclusive_group()
    monitor_group.add_argument(
        "-m",
        "--monitor",
        type=int,
        default=1,
        help="Monitor index from mss (0 = all, 1+ = individual; default 1; mutually exclusive with --capture-area)",
    )
    monitor_group.add_argument(
        "-a",
        "--capture-area",
        type=_capture_area_type,
        metavar="X,Y,W,H",
        help="Capture rectangle as left,top,width,height (mutually exclusive with --monitor)",
    )
    parser.add_argument(
        "-s",
        "--scaling-mode",
        choices=["letterbox", "crop", "stretch"],
        default="crop",
        help="How to scale to TinyTV display: letterbox (black bars), crop (center), or stretch (default crop)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=_quality_type,
        default=75,
        help="JPEG quality (1-100; default 75)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s")

    # Handle --list-devices
    if args.list_devices:
        list_devices()
        return

    # Compute variables from CLI args.
    monitor = args.monitor
    capture_area = args.capture_area
    quality = args.quality
    scaling_mode = args.scaling_mode

    # Find the right device.
    if args.device:
        if args.usb_id is not None or args.usb_serial_number is not None:
            parser.error("argument --device: not allowed with --usb-id or --usb-serial-number")
        device = args.device
    else:
        device = get_device_name(args.usb_id, args.usb_serial_number)
        LOGGER.info("Using device %s", device)

    # We could use serial.Serial as a context manager if we wanted to automatically close it when we don't need it
    # anymore.  But we need it for the entire life of the program, so we just keep it open.
    ser = serial.Serial(device, timeout=1)
    size = get_screen_size(ser)
    LOGGER.debug("TinyTV screen size: %dx%d", size[0], size[1])

    # We divide our work into three stages: capture, processing (scale and encode), and sending.  These each take
    # about the same amount of time per-image.  In the capture stage, we are mostly waiting for the image to be
    # copied.  In the processing stage, we are just running PIL image manipulation functions.  In the send stage, we
    # are mostly waiting for the TinyTV to read our data.  The overall slowest stage is the send stage.  You can get
    # close to optimal performance even if you combine the capture and processing threads, but separating them gives
    # us more headroom.

    # Mailboxes are used to pass data between threads.
    captured_image_mailbox: Mailbox[Image.Image] = Mailbox()
    jpeg_bytes_mailbox: Mailbox[bytes] = Mailbox()
    byte_count_mailbox: Mailbox[int] = Mailbox()

    # The stages are run in parallel threads.
    capture_stage: PipelineStage[None, Image.Image] = PipelineStage(
        name="capture",
        target=functools.partial(capture_image, monitor=monitor, capture_area=capture_area),
        out_mailbox=captured_image_mailbox,
    )
    process_and_encode_stage = PipelineStage(
        name="process_and_encode",
        in_mailbox=captured_image_mailbox,
        target=functools.partial(process_and_encode_image, size=size, scaling_mode=scaling_mode, quality=quality),
        out_mailbox=jpeg_bytes_mailbox,
    )
    send_stage: PipelineStage[bytes, int] = PipelineStage(
        name="send",
        in_mailbox=jpeg_bytes_mailbox,
        target=functools.partial(send_jpeg, ser),
        out_mailbox=byte_count_mailbox,
    )

    capture_stage.start()
    process_and_encode_stage.start()
    send_stage.start()

    LOGGER.debug("Capture thread: %i", capture_stage.native_id)
    LOGGER.debug("Process thread: %i", process_and_encode_stage.native_id)
    LOGGER.debug("Send thread:    %i", send_stage.native_id)

    # The show_stats function will run until the byte_count_mailbox shuts down, which happens if any of the threads
    # encounters an error: the PipelineStage will shut down its mailboxes, and that shutdown will propagate through
    # all the stages.
    show_stats(byte_count_mailbox)

    # At this point, the byte_count_mailbox has shut down, and the others will be shutting down as well.  We join the
    # outstanding threads, so that if any of them raise an Exception, that thread has time to print it before we exit.
    capture_stage.join()
    process_and_encode_stage.join()
    send_stage.join()

    # Test for errors from any of the stages.  If there are errors, then the default threading.excepthook will have
    # already printed it to stderr.  We just need to exit with a non-zero value to let the shell know that something
    # happened.  (Mind you, currently, we never stop without an exception like KeyboardInterrupt.)
    if capture_stage.exc or process_and_encode_stage.exc or send_stage.exc:
        sys.exit(1)


if __name__ == "__main__":
    main()
