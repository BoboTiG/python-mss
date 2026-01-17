#! /usr/bin/env python3

# This demo shows one common use case for MSS: capture the screen and
# write a real video file (MP4) rather than saving individual images.
#
# It's intentionally not a full "video encoding" course.  The goal is
# to explain the few concepts that show up throughout the program so
# you can read, tweak, and extend it.
#
# What tools are we using?
# ------------------------
#
# Most people first meet video encoding through the `ffmpeg` command.
# Under the hood, ffmpeg is built on the "libav*" C libraries.  In
# this demo we use PyAV (`import av`), which is a Pythonic wrapper
# around those libraries.
#
# PyAV docs: <https://pyav.basswood-io.com/docs/stable/>
# Note: the older docs at pyav.org are outdated; see
# <https://github.com/PyAV-Org/PyAV/issues/1574>.
# Caveats: <https://pyav.basswood-io.com/docs/stable/overview/caveats.html>
#
# Containers, streams, and codecs
# -------------------------------
#
# A file like `capture.mp4` is a *container*: it holds one or more
# *streams* (usually video and/or audio).  This demo writes one video
# stream.
#
# The container interleaves ("muxes") stream data so players can read
# everything in timestamp order. libav calls those pieces "packets".
# (In MP4 they're not literally network-style packets; the term is a
# longstanding libav abstraction.)
#
# A *codec* is the algorithm that compresses/decompresses a stream.
# For MP4 video, common codecs include H.264 and H.265.  This demo
# defaults to H.264 via `libx264`, because it's widely supported.  You
# can switch to hardware encoders (e.g. `h264_nvenc`) if available.
#
# Frames and frame reordering (I/P/B)
# ----------------------------------
#
# Video is encoded as a sequence of frames:
# - I-frames: complete images.
# - P-frames: changes from previous frames.
# - B-frames: changes predicted using both past *and future* frames.
#
# B-frames are why "the order frames are encoded/decoded" can differ
# from "the order frames are shown".  That leads directly to
# timestamps.
#
# Timestamps (PTS/DTS)
# --------------------
#
# Every frame has a *presentation timestamp* (PTS): when the viewer
# should see it.
#
# Encoders may output packets in a different order due to B-frames.
# Those packets also have a *decode timestamp* (DTS): when the decoder
# must decode them so the PTS schedule can be met.
#
# In this demo we set PTS on `VideoFrame`s and let libav/PyAV
# propagate timestamps into the encoded packets.
#
# Time base
# ---------
#
# Timestamps are integers, and their unit is a fraction of a second
# called the *time base*.  For example, with a time base of 1/90000, a
# timestamp of 90000 means "1 second".  PyAV will convert between time
# bases when needed, but you must set them consistently where you
# generate timestamps.
#
# See <https://pyav.basswood-io.com/docs/stable/api/time.html>
#
# This demo uses a time base of 1/90000 (a common MPEG-derived choice).
#
# Performance (why multiple threads?)
# ----------------------------------
#
# Capturing frames, converting them to `VideoFrame`s, encoding, and
# muxing are separate stages.  This demo pipelines those stages across
# threads so that (for example) encoding can run while the next screen
# grab is happening.  The comments at the top of common/pipeline.py
# describe pipelining in detail.
#
# The slowest stage typically limits overall FPS.  Usually, that's the
# encoder.
#
# On an idle system (rough guide; will vary widely):
# - libx264, 1920x1080: ~80 fps
# - libx264, 3840x2160: ~18 fps
# - h264_nvenc, 1920x1080: ~190 fps
# - h264_nvenc, 3840x2160: ~41 fps

import argparse
import logging
import signal
import time
from collections import deque
from collections.abc import Generator, Iterable, Sequence
from fractions import Fraction
from functools import partial
from math import floor
from threading import Event
from typing import Any

import av
import numpy as np
from si_prefix import si_format

import mss
from common.pipeline import Mailbox, PipelineStage


# These are the options you'd give to ffmpeg that it sends to the
# video codec.  The options you can use here can be listed with
# `ffmpeg -help encoder=libx264`, or whatever encoder you're using for
# this demo's `--codec` flag.  The options for each encoder are described
# in more detail in `man ffmpeg-codecs`.
CODEC_OPTIONS = {
    # The "high" profile means that the encoder can use some H.264
    # features that are widely supported, but not mandatory.  If
    # you're using a codec other than H.264, you'll need to comment
    # out this line: the relevant features are already part of the
    # main profile in later codecs like H.265, VP8, VP9, and AV1.
    "profile": "high",
    # The "medium" preset is as good of a preset as any for a demo
    # like this.  Different codecs have different presets; the
    # h264_nvenc actually prefers "p4", but accepts "medium" as a
    # similar preset.
    "preset": "medium",
    # 6 Mbit/sec is vaguely the ballpark for a good-quality video at
    # 1080p and 30 fps, but there's a lot of variation.  We're just
    # giving the target bitrate: the second-to-second bitrate will
    # vary a lot, and slowly approach this bitrate.  If you're trying
    # this on a nearly-still screen, though, then the actual bitrate
    # will be much lower, since there's not much motion to encode!
    "b": "6M",
    # Let the encoder hold some frames for analysis, and flush them
    # later.  This especially helps with the hardware-accelerated
    # codecs.
    "rc-lookahead": "40",
}


TIME_BASE = Fraction(1, 90000)

# Currently, MSS doesn't give us information about the display's
# colorspace.  See where this is used below for more information.
DISPLAY_IS_SRGB = False

LOGGER = logging.getLogger("video-capture")


def video_capture(
    fps: int,
    sct: mss.base.MSSBase,
    monitor: mss.models.Monitor,
    shutdown_requested: Event,
) -> Generator[tuple[mss.screenshot.ScreenShot, float], None, None]:
    # Keep track of the time when we want to get the next frame.  We
    # limit the frame time this way instead of sleeping 1/fps sec each
    # frame, since we want to also account for the time taken to get
    # the screenshot and other overhead.
    #
    # Repeatedly adding small floating-point numbers to a total does
    # cause some numeric inaccuracies, but it's small enough for our
    # purposes.  The program would have to run for three months to
    # accumulate one millisecond of inaccuracy.
    next_frame_at = time.monotonic()

    # Keep running this loop until the main thread says we should
    # stop.
    while not shutdown_requested.is_set():
        # Wait until we're ready.  This should, ideally, happen every
        # 1/fps second.
        while (now := time.monotonic()) < next_frame_at:
            time.sleep(next_frame_at - now)

        # Capture a frame, and send it to the next processing stage.
        screenshot = sct.grab(monitor)
        yield screenshot, now

        # We try to keep the capture rate at the desired fps on
        # average.  If we can't quite keep up for a moment (such as if
        # the computer is a little overloaded), then we'll accumulate
        # a bit of "timing debt" in next_frame_at: it'll be a little
        # sooner than now + one frame.  We'll hopefully be able to
        # catch up soon.
        next_frame_at = next_frame_at + (1 / fps)

        # If we've accumulated over one frame's worth of timing debt,
        # then that will say that next_frame_at is sooner than now.
        # If we're accumulating too much debt, we want to wipe it out,
        # rather than having a huge burst of closely-spaced captures
        # as soon as we can get back to our desired capture rate.
        # When we wipe that out, we still try to preserve the timing
        # cycle's phase to keep the capture cadence smooth, rather
        # than having a jittery burst of closely-spaced captures.  In
        # other words, we increment next_frame_at by a multiple of the
        # desired capture period.
        if next_frame_at < now:
            missed_frames = floor((now - next_frame_at) * fps)
            next_frame_at += (missed_frames + 1) / fps


def video_process(
    screenshot_and_timestamp: Iterable[
        tuple[mss.screenshot.ScreenShot, float]
    ],
) -> Generator[av.VideoFrame, None, None]:
    # We track when the first frame happened so we can make PTS start
    # at 0.  Many video players and other tools expect that.
    first_frame_at: float | None = None

    for screenshot, timestamp in screenshot_and_timestamp:
        # Avoiding extra pixel copies
        # ---------------------------
        #
        # Copying a full frame of pixels is expensive.  On typical
        # hardware, a plain CPU memcpy of a 4K BGRA image can cost on
        # the order of ~3ms by itself, which is a big chunk of a 30fps
        # budget (33ms) and an even bigger chunk of a 60fps budget
        # (16.7ms).
        #
        # So we want to be careful about the *conversion* step from an
        # MSS `ScreenShot` to a PyAV `VideoFrame`.  Ideally, that step
        # should reuse the same underlying bytes rather than creating
        # additional intermediate copies.
        #
        # Buffers in Python
        # -----------------
        #
        # Many Python objects expose their underlying memory via the
        # "buffer protocol".  A buffer is just a view of raw bytes
        # that other libraries can interpret without copying.
        #
        # Common buffer objects include: `bytes`, `bytearray`,
        # `memoryview`, and `array.array`.  `screenshot.bgra` is also
        # a buffer (currently it is a `bytes` object, though that
        # detail may change in the future).
        #
        # Minimum-copy path: ScreenShot -> NumPy -> VideoFrame
        # ----------------------------------------------------
        #
        # `np.frombuffer()` creates an ndarray *view* of an existing
        # buffer (no copy).  Reshaping also stays as a view.
        #
        # PyAV's `VideoFrame.from_ndarray()` always copies the data
        # into a new frame-owned buffer.  For this demo we use the
        # undocumented `VideoFrame.from_numpy_buffer()`, which creates
        # a `VideoFrame` that shares memory with the ndarray.
        ndarray = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        ndarray = ndarray.reshape(screenshot.height, screenshot.width, 4)
        frame = av.VideoFrame.from_numpy_buffer(ndarray, format="bgra")

        # Set the PTS and time base for the frame.
        if first_frame_at is None:
            first_frame_at = timestamp
        frame.pts = int((timestamp - first_frame_at) / TIME_BASE)
        frame.time_base = TIME_BASE

        # If we know the colorspace of our frames, mark them
        # accordingly.  See the comment where we set these attributes
        # on video_stream for details.
        if DISPLAY_IS_SRGB:
            frame.colorspace = av.video.reformatter.Colorspace.ITU709
            frame.color_range = av.video.reformatter.ColorRange.JPEG

        yield frame


def video_encode(
    video_stream: av.video.stream.VideoStream, frames: Iterable[av.VideoFrame]
) -> Generator[Sequence[av.Packet], None, None]:
    for frame in frames:
        yield video_stream.encode(frame)
    # Our input has run out.  Flush the frames that the encoder still
    # is holding internally (such as to compute B-frames).
    yield video_stream.encode(None)


def show_stats(
    packet_batches: Iterable[Sequence[av.Packet]],
) -> Iterable[Sequence[av.Packet]]:
    """Display streaming statistics (FPS and throughput).

    Statistics are displayed over a 100-frame sliding window.

    FPS indicates how fast the entire pipeline can run as a whole, not
    any individual stage.
    """
    # The start time is only used for showing the clock.  The actual
    # timing stats use packet timestamps (ultimately derived from the
    # frame PTS we compute during capture).
    start_time = time.monotonic()
    time_deque: deque[int] = deque(maxlen=100)
    bit_count_deque: deque[int] = deque(maxlen=100)
    next_display_update = 0.0
    last_status_len = 0

    for frame_count, packet_batch in enumerate(packet_batches):
        # Yield the packet data immediately, so the mux gets it as
        # soon as possible, while we update our stats.
        yield packet_batch

        for packet in packet_batch:
            # FPS from timestamps: why DTS, not PTS?
            #
            # Intuitively, you'd expect to compute FPS from PTS (the
            # time the viewer should *see* each frame).  But encoders
            # can reorder frames internally (especially with
            # B-frames), so packets may come out in a different order
            # than PTS.
            #
            # If we update a sliding window with out-of-order PTS
            # values, the window start/end can "wiggle" even when the
            # pipeline is steady, which makes the displayed FPS noisy.
            #
            # DTS is the time order the decoder must process packets.
            # Packets are emitted in DTS order, so using DTS gives a
            # stable, monotonic timeline for the sliding window.
            time_deque.append(packet.dts)
            bit_count = packet.size * 8
            bit_count_deque.append(bit_count)

        now = time.monotonic()
        if now >= next_display_update and len(time_deque) > 1:
            next_display_update = now + 0.1
            running_time = now - start_time
            running_minutes = int(running_time / 60)
            running_seconds = int(running_time % 60)
            window_secs = (time_deque[-1] - time_deque[0]) * TIME_BASE
            # We can't use the last frame in the window when we divide
            # by window_secs; that would be a fencepost error.
            window_frames = len(time_deque) - 1
            window_bits = sum(bit_count_deque) - bit_count_deque[-1]
            fps = window_frames / window_secs
            bits_per_sec = int(window_bits / window_secs)
            line = (
                f"{running_minutes:02d}:{running_seconds:02d} "
                f"frame {frame_count}: {fps:.2f} fps, "
                f"{si_format(bits_per_sec, precision=2)}bps"
            )
            this_status_len = len(line)
            full_line = f"\r{line}{' ' * (last_status_len - this_status_len)}"
            print(full_line, end="")
            last_status_len = this_status_len
    # Near shutdown the encoder flush can emit packets in large
    # bursts, and we also throttle status updates (to avoid spamming
    # the terminal).  That combination means the last displayed line
    # may be stale or not representative of the final frames.  Rather
    # than leaving potentially misleading numbers on screen, erase the
    # status display.
    print(f"\r{' ' * last_status_len}\r", end="")


def mux(
    avmux: av.container.OutputContainer,
    packet_batches: Iterable[Sequence[av.Packet]],
) -> None:
    for packet_batch in packet_batches:
        avmux.mux(packet_batch)


def parse_region(s: str) -> tuple[int, int, int, int]:
    """Parse comma-separated region string into (left, top, right, bottom)."""
    parts = s.split(",")
    if len(parts) != 4:
        msg = "region must be four comma-separated integers"
        raise argparse.ArgumentTypeError(msg)
    try:
        return tuple(int(p.strip()) for p in parts)  # type: ignore[return-value]
    except ValueError as e:
        msg = "region values must be integers"
        raise argparse.ArgumentTypeError(msg) from e


def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    # If we don't enable PyAV's own logging, a lot of important error
    # messages from libav won't be shown.
    av.logging.set_level(av.logging.VERBOSE)

    parser = argparse.ArgumentParser(
        description="Capture screen video to MP4 file"
    )
    parser.add_argument(
        "-f",
        "--fps",
        type=int,
        default=30,
        help="frames per second (default: 30)",
    )
    monitor_group = parser.add_mutually_exclusive_group()
    monitor_group.add_argument(
        "-m",
        "--monitor",
        type=int,
        default=1,
        help="monitor ID to capture (default: 1)",
    )
    monitor_group.add_argument(
        "-r",
        "--region",
        type=parse_region,
        metavar="LEFT,TOP,RIGHT,BOTTOM",
        help="region to capture as comma-separated coordinates",
    )
    parser.add_argument(
        "-c",
        "--codec",
        default="libx264",
        help=(
            'video codec implementation, same as the ffmpeg "-c:v" flag.  '
            'Run "python3 -m av --codecs" for a full list.  '
            "(default: libx264.  Try h264_nvenc for Nvidia "
            "hardware encoding.)"
        ),
    )
    parser.add_argument(
        "-d",
        "--duration-secs",
        type=float,
        help="Duration to record (default: no limit)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="capture.mp4",
        help="output filename (default: capture.mp4)",
    )
    args = parser.parse_args()

    fps = args.fps
    codec = args.codec
    filename = args.output
    duration_secs = args.duration_secs

    with mss.mss() as sct:
        if args.region:
            left, top, right, bottom = args.region
            monitor = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        else:
            monitor = sct.monitors[args.monitor]

        # We don't pass the container format to av.open here, so it
        # will choose it based on the extension: .mp4, .mkv, etc.
        with av.open(filename, "w") as avmux:
            # We could initialize video_stream in video_encode, but
            # doing it here means that we can open it before starting
            # the capture thread, which avoids a warmup frame (one
            # that takes longer to encode because the encoder is just
            # starting).
            #
            # The rate= parameter here is just the nominal frame rate:
            # some tools (like file browsers) might display this as
            # the frame rate.  But we actually control timing via the
            # pts and time_base values on the frames themselves.
            video_stream = avmux.add_stream(
                codec, rate=fps, options=CODEC_OPTIONS
            )

            # Ideally, we would set attributes such as colorspace,
            # color_range, color_primaries, and color_trc here to
            # describe the colorspace accurately.  Otherwise, the
            # player has to guess whether this was recorded on an sRGB
            # Windows machine, a Display P3 Mac, or if it's using
            # linear RGB.  Currently, MSS doesn't give us colorspace
            # information (DISPLAY_IS_SRGB is always False in this
            # demo), so we don't try to specify a particular
            # colorspace.  However, if your application knows the
            # colorspace you're recording from, then you can set those
            # attributes on the stream and the frames accordingly.
            #
            # These properties on the stream (actually, they're
            # attached to its CodecContext) are used to tell the
            # stream and container how to label the video stream's
            # colorspace.  There are similar attributes on the frame
            # itself; those are used to identify its colorspace, so
            # the codec can do the correct RGB to YUV conversion.
            if DISPLAY_IS_SRGB:
                # color_primaries=1 is libavutil's AVCOL_PRI_BT709;
                # PyAV doesn't define named constants for color
                # primaries.
                video_stream.color_primaries = 1
                # What PyAV refers to as ITU709 is more commonly known
                # as BT.709.
                video_stream.colorspace = (
                    av.video.reformatter.Colorspace.ITU709
                )
                # The "JPEG" color range is saying that we're using a
                # color range like a computer, not like broadcast TV.
                video_stream.color_range = av.video.reformatter.ColorRange.JPEG
                # PyAV doesn't define named constants for TRCs, so we
                # pass it a numeric value.  Technically, sRGB's
                # transformation characteristic is
                # AVCOL_TRC_IEC61966_2_1 (13).  It's nearly the same
                # as BT.709's TRC, so some video encoders will tag it
                # as AVCOL_TRC_BT709 (1) instead.
                video_stream.color_trc = 13

            video_stream.width = monitor["width"]
            video_stream.height = monitor["height"]
            # There are multiple time bases in play (stream, codec
            # context, per-frame).  Depending on the container and
            # codec, some of these might be ignored or overridden.  We
            # set the desired time base consistently everywhere, so
            # that the saved timestamps are correct regardless of what
            # format we're saving to.
            video_stream.time_base = TIME_BASE
            video_stream.codec_context.time_base = TIME_BASE
            # `pix_fmt` here describes the pixel format we will *feed*
            # into the encoder (not necessarily what the encoder will
            # store in the bitstream).  H.264 encoders ultimately
            # convert to a YUV format internally.
            #
            # If the encoder accepts BGRA input (e.g., h264_nvenc), we
            # can hand it MSS's BGRA frames directly and avoid an
            # extra pre-conversion step on our side.
            #
            # If the encoder doesn't accept BGRA input (e.g.,
            # libx264), PyAV will insert a conversion step
            # automatically.  In that case, we let the codec choose
            # the pix_fmt it's going to expect.
            #
            # Note: the alpha channel is ignored by H.264.  We may
            # effectively be sending BGRx/BGR0.  But PyAV's VideoFrame
            # only exposes "bgra" as the closest supported format.
            if any(f.name == "bgra" for f in video_stream.codec.video_formats):
                video_stream.pix_fmt = "bgra"
            # We open (initialize) the codec explicitly here.  PyAV
            # will automatically open it the first time we call
            # video_stream.encode, but the time it takes to set the
            # codec up means the first frame would be particularly
            # slow.
            video_stream.open()

            shutdown_requested = Event()

            mailbox_screenshot: Mailbox[
                tuple[mss.screenshot.ScreenShot, float]
            ] = Mailbox()
            mailbox_frame: Mailbox[av.VideoFrame] = Mailbox()
            mailbox_packet_to_stats: Mailbox[Sequence[av.Packet]] = Mailbox()
            mailbox_packet_to_mux: Mailbox[Sequence[av.Packet]] = Mailbox()

            stage_video_capture = PipelineStage(
                name="video_capture",
                target=partial(
                    video_capture,
                    fps,
                    sct,
                    monitor,
                    shutdown_requested,
                ),
                out_mailbox=mailbox_screenshot,
            )
            stage_video_process = PipelineStage(
                name="video_process",
                in_mailbox=mailbox_screenshot,
                target=partial(video_process),
                out_mailbox=mailbox_frame,
            )
            stage_video_encode = PipelineStage(
                name="video_encode",
                in_mailbox=mailbox_frame,
                target=partial(video_encode, video_stream),
                out_mailbox=mailbox_packet_to_stats,
            )
            stage_show_stats = PipelineStage(
                name="show_stats",
                in_mailbox=mailbox_packet_to_stats,
                target=show_stats,
                out_mailbox=mailbox_packet_to_mux,
            )
            stage_mux = PipelineStage(
                name="stream_mux",
                in_mailbox=mailbox_packet_to_mux,
                target=partial(mux, avmux),
            )

            stage_mux.start()
            stage_show_stats.start()
            stage_video_process.start()
            stage_video_encode.start()
            stage_video_capture.start()

            LOGGER.debug("Native thread IDs:")
            LOGGER.debug("  Capture:    %s", stage_video_capture.native_id)
            LOGGER.debug("  Preprocess: %s", stage_video_process.native_id)
            LOGGER.debug("  Encode:     %s", stage_video_encode.native_id)
            LOGGER.debug("  Mux:        %s", stage_mux.native_id)

            old_sigint_handler = signal.getsignal(signal.SIGINT)

            def sigint_handler(_signum: int, _frame: Any) -> None:
                # Restore the default behavior, so if our shutdown
                # doesn't work because of a bug in our code, the user
                # can still press ^C again to terminate the program.
                # (The default handler is also in
                # signal.default_int_handler, but that's not
                # documented.)
                signal.signal(signal.SIGINT, old_sigint_handler)
                # The status line will typically be visible, so start
                # a fresh line for this message.
                print("\nShutting down")
                shutdown_requested.set()

            old_sigint_handler = signal.signal(signal.SIGINT, sigint_handler)

            print("Starting video capture.  Press Ctrl-C to stop.")

            if duration_secs is not None:
                stage_video_capture.join(timeout=duration_secs)
                # Either the join timed out, or we processed a ^C and
                # requested it exit.  Either way, it's safe to set the
                # shutdown event again, and return to our normal
                # processing loop.
                shutdown_requested.set()

            stage_video_capture.join()
            stage_video_process.join()
            stage_video_encode.join()
            stage_show_stats.join()
            stage_mux.join()

            # PyAV may insert an implicit conversion step between the
            # frames we provide and what the encoder actually accepts
            # (pixel format, colorspace, etc.).  When that happens,
            # `video_stream.reformatter` gets set.
            #
            # This is useful to know for performance: those
            # conversions are typically CPU-side work and can become a
            # bottleneck.  Hardware-accelerated encoders, such as
            # `h264_nvenc`, often accept BGRx, and can perform the
            # conversion using specialized hardware.
            #
            # We already know that libx264 doesn't accept RGB input,
            # so we don't warn about that.  (There is a libx264rgb,
            # but that writes to a different H.264 format.)  We just
            # want to warn about other codecs, since some of them
            # might have ways to use BGRx input, and the programmer
            # might want to investigate.
            #
            # Note: `reformatter` is created lazily, so it may only be
            # set after frames have been sent through the encoder,
            # which is why we check it at the end.
            if video_stream.reformatter is not None and codec != "libx264":
                LOGGER.warning(
                    "PyAV inserted a CPU-side pixel-format/colorspace "
                    "conversion step; this can reduce FPS.  Check the "
                    "acceptable pix_fmts for this codec, and see if one "
                    "of them can accept some variation of BGRx input "
                    "directly."
                )


if __name__ == "__main__":
    main()
