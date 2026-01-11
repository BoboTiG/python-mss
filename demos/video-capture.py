#! /usr/bin/env python3

# In one test, here's some numbers this program could achieve.  This
# is just meant as a rough guide; your results will almost certainly
# vary significantly.
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
from common.pipeline import Mailbox, PipelineStage
from si_prefix import si_format

import mss

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

# There are a lot of different places in a video encoding pipeline
# where time_base matters, and they don't necessarily have to be the
# same, so the time base has to be set on several objects.  In this
# program, we do use a common time base of 1/90000 seconds everywhere.
# This is a common standard, from the MPEG world.
TIME_BASE = Fraction(1, 90000)

LOGGER = logging.getLogger("video-capture")

def video_capture(
    fps: int,
    sct: mss.base.MSSBase,
    monitor: mss.models.Monitor,
    shutdown_requested: Event,
) -> Generator[tuple[mss.screenshot.ScreenShot, float], None, None]:
    next_frame_at = time.monotonic()
    capture_period = 1 / fps
    while not shutdown_requested.is_set():
        # Wait until we're ready.
        while (now := time.monotonic()) < next_frame_at:
            time.sleep(next_frame_at - now)

        # Capture and yield a frame.
        screenshot = sct.grab(monitor)
        yield screenshot, now

        # We try to keep the capture rate at the desired fps on
        # average.  If we can't quite keep up for a moment (such as if
        # the computer is a little overloaded), then we'll accumulate
        # a bit of "timing debt" in next_frame_at: it'll be a little
        # sooner than now + one frame.  We'll hopefully be able to
        # catch up soon.
        next_frame_at = next_frame_at + capture_period

        # If we've accumulated over one frame's worth of catch-up,
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
            next_frame_at += (missed_frames + 1) * capture_period


def video_process(
    screenshot_and_timestamp: Iterable[
        tuple[mss.screenshot.ScreenShot, float]
    ],
) -> Generator[av.VideoFrame, None, None]:
    first_frame_at: float | None = None
    for screenshot, timestamp in screenshot_and_timestamp:
        ndarray = np.frombuffer(screenshot.bgra, dtype=np.uint8)
        ndarray = ndarray.reshape(screenshot.height, screenshot.width, 4)
        # from_numpy_buffer isn't documented.  from_ndarray is, but
        # that copies the data.  That's slow enough to slow things
        # down to the point of being a real bottleneck!
        frame = av.VideoFrame.from_numpy_buffer(ndarray, format="bgra")
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


def show_stats(packet_batches: Iterable[Sequence[av.Packet]]) -> Iterable[Sequence[av.Packet]]:
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
            # unstable.  Using DTS consistently makes the timing quite
            # stable, and over the 100-frame window, still quite
            # precise.
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
            line = (f"{running_minutes:02d}:{running_seconds:02d} "
                    f"frame {frame_count}: {fps:.2f} fps, "
                    f"{si_format(bits_per_sec, precision=2)}bps")
            this_status_len = len(line)
            full_line = f"\r{line}{' ' * (last_status_len - this_status_len)}"
            print(full_line, end="")
            last_status_len = this_status_len
    # It's difficult to correctly print the fps and bitrate near the
    # tail, since we get the last many frames as a big batch.  Instead
    # of leaving misleading information on the screen, we erase the
    # status display.
    print(f"\r{' ' * last_status_len}\r", end="")


def mux(avmux: av.container.OutputContainer, packet_batches: Iterable[Sequence[av.Packet]]) -> None:
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
        "--fps",
        type=int,
        default=30,
        help="frames per second (default: 30)"
    )
    monitor_group = parser.add_mutually_exclusive_group()
    monitor_group.add_argument(
        "--monitor",
        type=int,
        default=1,
        help="monitor ID to capture (default: 1)"
    )
    monitor_group.add_argument(
        "--region",
        type=parse_region,
        metavar="LEFT,TOP,RIGHT,BOTTOM",
        help="region to capture as comma-separated coordinates"
    )
    parser.add_argument(
        "--codec",
        default="libx264",
        help="video codec (default: libx264; try h264_nvenc for Nvidia hardware encoding)"
    )
    parser.add_argument(
        "--output",
        default="capture.mp4",
        help="output filename (default: capture.mp4)"
    )
    args = parser.parse_args()

    fps = args.fps
    codec = args.codec
    filename = args.output

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
            # doesn't support reading frames in BGR0, only BGRA.
            # H.264 doesn't support an alpha channel anyway, so we can
            # just send it BGR0 frames and tell it they're BGRA.
            if any(f.name == "bgra" for f in video_stream.codec.video_formats):
                video_stream.pix_fmt = "bgra"
            # We open (initialize) the codec explicitly here.  PyAV
            # will automatically open it the first time we call
            # video_stream.encode, but the time it takes to set the
            # codec up means the first frame would be particularly
            # slow.
            video_stream.open()

            shutdown_requested = Event()
            def sigint_handler(_signum: int, _frame: Any) -> None:
                # The status line will typically be visible, so start
                # a fresh line for this message.
                print("\nShutting down")
                shutdown_requested.set()
            signal.signal(signal.SIGINT, sigint_handler)

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

            LOGGER.debug("Thread IDs:")
            LOGGER.debug("  Capture:    %s", stage_video_capture.native_id)
            LOGGER.debug("  Preprocess: %s", stage_video_process.native_id)
            LOGGER.debug("  Encode:     %s", stage_video_encode.native_id)
            LOGGER.debug("  Mux:        %s", stage_mux.native_id)

            print("Starting video capture.  Press Ctrl-C to stop.")

            stage_video_capture.join()
            stage_video_process.join()
            stage_video_encode.join()
            stage_show_stats.join()
            stage_mux.join()

            if codec != "libx264" and video_stream.reformatter is not None:
                LOGGER.warning("Software encoder is in a hardware encoding "
                               "path; this may slow things down")


if __name__ == "__main__":
    main()
