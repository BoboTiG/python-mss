#! /usr/bin/env python3

# This demo isn't meant to be a comprehensive explanation of video
# encoding.  There are, however, some concepts that are unavoidable
# when converting from a sequence of snapshots to a video file.  We'll
# go over some of those here.
#
# The descriptions given here are simplified.  It doesn't go into the
# more obscure details, like H.264 switching frames or the AAC priming
# delay.  Nevertheless, this should be enough to get the concepts
# you'll need to understand and build on this demo.
#
#
# libav
# -----
#
# If you care enough about video files to be reading this, you've
# probably used ffmpeg.  This is a Swiss Army Knife of video file
# manipulation.
#
# The ffmpeg tool is based on several libraries, which are part of
# ffmpeg, and widely used elsewhere:
# 
# - libavcodec: Encoding/decoding library
# - libavfilter: Graph-based frame editing library
# - libavformat: I/O and muxing/demuxing library
# - libavdevice: Special devices muxing/demuxing library
# - libavutil: Common utility library
# - libswresample: Audio resampling, format conversion and mixing
# - libswscale: Color conversion and scaling library
#
# In this demo, I just refer to these collectively as "libav".  Think
# of these as the library version of ffmpeg.  We mostly use libavcodec
# and libavformat, but that detail isn't something we see in Python:
# all these libraries are essentially one giant bundle as far as we
# care.
#
# The libav libaries are in C.  We use the PyAV library.  This is not
# simply bindings or a direct translation of the libav C API to
# Python, but rather, a library that's based on libav, but meant to be
# more Pythonic.  
#
# [note: it's important to include the fact that pyav.org has outdated
# docs, since they show up prominently in Google searches.  The link
# to the GitHub issue is just to tell people that the ]
#
# The docs for PyAV are at <https://pyav.basswood-io.com/docs/stable/>.
# The older docs at pyav.org are outdated; see
# <https://github.com/PyAV-Org/PyAV/issues/1574>.
#
# There was briefly a fork called basewood-av, but it has since been
# discontinued and merged back into PyAV; see
# <https://github.com/PyAV-Org/PyAV/discussions/1827>.  Despite the
# domain name, pyav.basswood-io.com hosts the current official PyAV
# documentation, not fork-specific docs.
#
# The PyAV developers are separate from ffmpeg, and there is a bit of
# a difference in the approaches that PyAV takes.  See also
# https://pyav.basswood-io.com/docs/stable/overview/caveats.html
#
#
# Container Files
# ---------------
#
# A single file, like kittycat.mp4, is called a "container" in media
# file terms.  This is a collection of "streams" (sometimes called
# "elementary streams"), all woven together.
#
# It might contain just a video stream (like we do here), just an
# audio stream (like in a .m4a file, which is just a renamed .mp4
# file), or both (most common).  It might also contain several of
# each; for instance, different languages will usually be in separate
# audio streams.  There are other stream types, like subtitles, as
# well.
#
# Weaving these streams together is called "multiplexing", or "muxing"
# for short.  Each stream's data gets bundled into "chunks" that are
# typically called "packets".  The container keeps packets from the
# same time, but different streams, close to each other in the file.
#
# (By the way, the term "packet" is a holdover from MPEG-2 and before.
# Technically, MP4 files don't have packets: they have chunks, which
# can hold AAC frames, H.264 NALs, etc.  The data that used to be in
# MPEG-2 packet headers is now in MP4 tables.  To keep the terminology
# consistent between codecs and container formats, libav refers to the
# objects encapsulating all this as packets, regardless of the codec
# or container format.)
#
# For instance, at the beginning of the file, you might have one audio
# packet covering the first 21 ms, then a subtitle packet covering the
# first several seconds, then seven video packets each covering 3 ms,
# followed by another audio packet for the next 21 ms, and so on.
#
#
# Video Codecs
# ------------
#
# Within an MP4 file, the video can be stored in a lot of different
# formats.  These are the most common:
#
# - MPEG-2: used by DVDs, not much else anymore.
# - MPEG-4 Part 2: also known as DivX.  Very popular in the early 2000s,
#   not seen much anymore except older archives.
# - H.264: commonly used by BluRay, many streaming services, and many
#   MP4 files in the wild.
# - H.265: increasingly used, but not supported by older hardware.
# - AV1 and VP9: used by some streaming services; hardware support
#   varies, so these are typically offered alongside H.264 (or H.265)
#   as fallbacks.
#
# These are all stream formats.  There are many libraries that can
# create these files.  These libraries are known as "codecs".  In
# some contexts, the word "codec" is also used to name the stream
# format itself, so "H.264" might sometimes be called a codec.
#
# In this demo, we use H.264, since it's the most common.  You can
# also specify other codecs.
#
# In ffmpeg, and the av libraries that we use here, the best codec for
# H.264 that doesn't require any specific hardware is libx264.  There
# are also faster ones that are hardware-accelerated, such as
# h264_nvenc which uses specialized chips on Nvidia video cards.
#
#
# Frame Types
# -----------
#
# Reference: https://en.wikipedia.org/wiki/Video_compression_picture_types
#
# [Note: We can probably just give a brief description of the frame
# types.]
#
# The reason that video files can compress so well, much better than
# storing a JPEG for each frame, is that the file often can describe
# just the motion.  In a video of a cat meowing, the first frame will
# have everything that's visible: the room in the background, the
# entire cat, the whole thing.  We call a video frame that stores the
# whole picture an "I-frame".
#
# But the second frame just has to talk about what's changed in that
# 1/30 sec: it can just say that the tail moved this much to the left,
# the eyes closed slightly, what the now-visible bits of the eyelids
# look like, what's changed about the ear when it moved, etc.  We call
# this sort of frame, one that just stores the differences from a
# previous frame, a "P-frame".
#
# We still want to refresh the whole picture from scratch from time to
# time.  Since the differences between video frames are compressed,
# they're also imperfect.  Over time, these imperfections can
# accumulate.  Also, sometimes a frame may have been lost between when
# we store it and when the viewer sees it, such as if we made a DVD
# that later got scratched; we want to let the viewer recover from
# such a situation.  To keep things clean, we sometimes send out a new
# I-frame, redrawing the whole picture anew.  This normally happens
# about every 0.5 to 2 seconds, depending on the program's purpose.
# The group of pictures starting with a fresh I-frame is,
# straightforwardly enough, called a "group of pictures" (GOP).
#
# Sometimes, it's useful for a frame to give motion based not just on
# the past, but also the future.  For instance, when the cat's mouth
# first starts to open, you might want to say "look ahead at how the
# inside of the mouth looks when it's totally open, and draw just this
# tiny sliver of it now."  These are called "B-frames".
#
# A GOP usually arranges these frame types in a cadence, like
# IBBPBBPBB....  The specifics are up to the encoder, but the user can
# normally configure it to some degree.
#
#
# Timestamps
# ----------
#
# [note: Managing the PTS is a big part of the code, so I want to
# describe it.  The DTS is also worth at least highlighting, as is the
# fact that packets from the encoder may be in a different order than
# presentation order.]
#
# In a video file, time is very important.  It's used to synchronize
# audio and video, to prevent frame timing quantization from causing
# the clock to drift, and many other purposes.
#
# The time at which each frame should be shown is called its
# "presentation time stamp", or "PTS".  Normally, the PTS of the first
# frame is 0, and the rest of the video file is based on that.
#
# Because B-frames can require future frames to interpret, the future
# frames they depend on have to be decoded first.  That means that the
# order in which frames are decoded can be different from the order in
# which they are presented.  This leads to a second timestamp on each
# frame: the "decoding time stamp", or "DTS".
#
# Different container formats store the timestamps in different
# places: the container's structures, the packet headers, the streams,
# etc.  Because of this, there are multiple places that carry
# timestamps.  You can just set the timestamp on the video frame, and
# libav will propagate it from there to the packets and so forth.
#
#
# Time Base
# ---------
#
# [note: Most people new to video encoding may assume that timestamps
# are in float or integer nanoseconds or something, so the concept of
# the time base is significant.  We also attach it to multiple
# objects: the container object, the video stream context object, and
# each frame.  So, the reason we do that is worth noting.  Preserve the
# link to the PyAV docs.]
#
# In most video file formats, the time isn't specified in predefined
# units like nanoseconds.  Instead, in your video file, you specify
# the time units you're using, a fraction of a second.  This is called
# your time base.
#
# There are a lot of different places in a video encoding pipeline
# where you set a time base: everywhere that might need to encode a
# timestamp.  They don't necessarily have to be the same (PyAV will
# convert between the different time bases as needed), so the time
# base has to be set on several objects.  See also
# <https://pyav.basswood-io.com/docs/stable/api/time.html>
#
# In this demo, we use a common time base of 1/90000 sec everywhere.
# This is a common standard, from the MPEG world.  It became a
# standard because it can exactly represent 24 fps (film), 25 fps
# (European TV), 30 fps (US TV, nominally), and 30000/1001 fps (about
# 29.97, US broadcast TV).
#
#
# Performance
# -----------
#
# This demo uses multiple threads to improve performance.  These
# threads are pipelined; see the comments at the start of
# common/pipeline.py for information about that concept.
#
# In a pipelined design, the slowest stage usually sets the overall
# rate.  Suppose you and your roommates are all doing the dishes:
# Alice collects dishes and scrapes off food, Bob washes the dishes,
# Carol rinses them, Dave dries them, and Evelyn puts them away.
# If the
#
# [note: A detailed description of pipelining threads is in
# common/pipeline.py.  This section should discuss the stages
# we're using, and note that the encoding stage is usually the
# bottleneck.]
#
#
#
# [note: Not sure where to integrate this, but make sure the numbers
# are somewhere.]
#
# In one test, here's some numbers this program could achieve, on an
# idle system.  This is just meant as a rough guide; your results will
# almost certainly vary significantly.
# - libx264, 1920x1080: 80 fps
# - libx264, 3840x2160: 18 fps
# - h264_nvenc, 1920x1080: 190 fps
# - h264_nvenc, 3840x2160: 41 fps

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


# These are the options you'd give to ffmpeg that would affect the
# video codec.
CODEC_OPTIONS = {
    # The "high" profile means that the encoder can use some H.264
    # features that are widely supported, but not mandatory.
    "profile": "high",
    # The "medium" preset is as good of a preset as any for a demo
    # like this.  Different codecs have different presets; the the
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

LOGGER = logging.getLogger("video-capture")


def video_capture(
    fps: int,
    sct: mss.base.MSSBase,
    monitor: mss.models.Monitor,
    shutdown_requested: Event,
) -> Generator[tuple[mss.screenshot.ScreenShot, float], None, None]:
    # Keep track of the time when we want to get the next frame.  We
    # limit the frame time this way instead of sleeping 1/30 sec each
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
        # 1/30 second.
        while (now := time.monotonic()) < next_frame_at:
            # 
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
    # We track when the first
    first_frame_at: float | None = None

    for screenshot, timestamp in screenshot_and_timestamp:
        # A screenshot's pixel data can take a long time to copy.
        # Just for the CPU to copy the bytes, on my hardware, takes
        # about 3ms for a 4k screenshot.  This means we want to be
        # very careful about how we want to get the data from the
        # ScreenShot object to the VideoFrame.
        #
        # In Python, there's a concept called a "buffer".  This is a
        # range of memory that can be shared between objects, so the
        # objects don't have to copy the data.  This is very common in
        # libraries like NumPy that work with very large datasets, and
        # interpret that data in different ways.
        #
        # The most common buffers are in extensions written in C, but
        # Python objects of type memoryview, bytes, bytearray, and
        # array.array are all buffers.  The screenshot.bgra attribute
        # is also a buffer.  (Currently, it's a bytes object, but this
        # may change in the future.)
        #
        # PyAV doesn't let you create a VideoFrame object directly
        # from pixel data in a buffer.  (It is possible to update the
        # data in a VideoFrame to point to a different buffer, but
        # that still allocates the memory first.)
        #
        # However, while it's not documented, PyAV does have the
        # from_numpy_buffer method (separately from the from_ndarray
        # method).  This creates a VideoFrame that shares memory with
        # a NumPy array.  We tell NumPy to create a new ndarray that
        # shares the screenshot's buffer, and create a VideoFrame that
        # uses that buffer.
        ndarray = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        ndarray = ndarray.reshape(screenshot.height, screenshot.width, 4)
        frame = av.VideoFrame.from_numpy_buffer(ndarray, format="bgra")
        # Set the PTS and time base for the frame.
        if first_frame_at is None:
            first_frame_at = timestamp
        frame.pts = int((timestamp - first_frame_at) / TIME_BASE)
        frame.time_base = TIME_BASE
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
    # timing stats all use the times we put in the captured frames.
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
            # The PTS would make more sense for logging FPS than the
            # DTS, but because of frame reordering, it makes the stats
            # a little bit unstable.  Using DTS consistently makes the
            # timing quite stable, and over the 100-frame window,
            # still quite precise.
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
    # It's difficult to correctly print the fps and bitrate near the
    # tail, since we get the last many frames as a big batch.  Instead
    # of leaving misleading information on the screen, we erase the
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
        "-f", "--fps", type=int, default=30, help="frames per second (default: 30)"
    )
    monitor_group = parser.add_mutually_exclusive_group()
    monitor_group.add_argument(
        "-m", "--monitor",
        type=int,
        default=1,
        help="monitor ID to capture (default: 1)",
    )
    monitor_group.add_argument(
        "-r", "--region",
        type=parse_region,
        metavar="LEFT,TOP,RIGHT,BOTTOM",
        help="region to capture as comma-separated coordinates",
    )
    parser.add_argument(
        "-c", "--codec",
        default="libx264",
        help="video codec (default: libx264; try h264_nvenc for Nvidia hardware encoding)",
    )
    parser.add_argument(
        "-d", "--duration-secs",
        type=float,
        help="Duration to record (default: no limit)",
    )
    parser.add_argument(
        "-o", "--output",
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
            video_stream.width = monitor["width"]
            video_stream.height = monitor["height"]
            # Setting the time_base on the stream is possible, but
            # isn't what we need (for reasons I'm unclear on): we need
            # to set it on the codec context.
            video_stream.codec_context.time_base = TIME_BASE
            # Assigning the pix_fmt is telling the video encoder what
            # we'll be sending it, not necessarily what it will
            # output.  If the codec supports BGRx inputs, then that's
            # the most efficient way for us to send it our frames.
            # Otherwise, there will be a software, CPU-side conversion
            # step when we send it our BGRx frames.  We're actually
            # probably sending it frames in BGR0, not BGRA, but PyAV
            # doesn't claim to support reading frames in BGR0, only
            # BGRA.  H.264 doesn't support an alpha channel anyway, so
            # we can just send it BGR0 frames and tell it they're BGRA.
            if any(
                f.name == "bgra" for f in video_stream.codec.video_formats
            ):
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

            print("Starting video capture.  Press Ctrl-C to stop.")

            old_sigint_handler = None
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
            signal.signal(signal.SIGINT, sigint_handler)

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

            if codec != "libx264" and video_stream.reformatter is not None:
                LOGGER.warning(
                    "Software encoder is in a hardware encoding "
                    "path; this may slow things down"
                )


if __name__ == "__main__":
    main()
