#! /usr/bin/env python3

# A lot of people want to use MSS to record a video of the screen.  Doing it really well can be difficult - there's a
# reason OBS is such a significant program - but the basics are surprisingly easy!
#
# There's a more advanced example, video-capture.py, that has more features, and better performance.  But this simple
# demo is easier to understand, because it does everything in a straightforward way, without any complicated features.
#
# Here, we're going to record the screen for 10 seconds, and save the result in capture.mp4, as an H.264 video stream.
#
# Sometimes, in film, cameramen will "undercrank", filming the action at a slower frame rate than how it will
# eventually be projected.  In that case, motion appears artificially sped up, either for comedy (like the Benny Hill
# TV show), or for fast and frenetic action (like Mad Max: Fury Road).
#
# In this demo, we put in the file a marker saying that it's at 30 fps.  But since this is a simple demo, your
# computer might not be able to keep up with writing video frames at that speed.  In that case, you'll see the same
# effect: sped-up motion.
#
# The full demo has several techniques to mitigate that.  First, it uses pipelined threads to let the video encoder
# use a full CPU core (often more, internally), rather than having to share a CPU core with all the other tasks.
# Second, it puts a timestamp marker on each frame saying exactly when it's supposed to be shown, rather than just
# saying to show all the frames at 30 fps.
#
# For this simple demo, though, we just record the frames and add them to the file one at a time.
#
# We use three libraries that don't come with Python: Pillow, PyAV, and (of course) MSS.  You'll need to install those
# with "pip install pillow av mss".  Normally, you'll want to install these into a venv; if you don't know about
# those, there are lots of great tutorials online.

import logging
import time

# Install the necessary libraries with "pip install av mss pillow".
import av
from PIL import Image

import mss

# These are the options you'd give to ffmpeg that would affect the way the video is encoded.  There are comments in
# the full demo that go into more detail.
CODEC_OPTIONS = {
    "profile": "high",
    "preset": "medium",
    "b": "6M",
    "rc-lookahead": "40",
}

# We'll try to capture at 30 fps, if the system can keep up with it (typically, that's possible at 1080p, but not at
# 4k).  Regardless of what the system can keep up with, we'll mark the file as being at 30 fps.
FPS = 30

# The program will exit after 10 seconds of recording.
CAPTURE_SECONDS = 10

# Within an MP4 file, the video can be stored in a lot of different formats.  In this demo, we use H.264, since it's
# the most widely supported.
#
# In ffmpeg, and the av libraries that we use here, the best codec for H.264 that doesn't require any specific
# hardware is libx264.  There are faster ones that are hardware-accelerated, such as h264_nvenc which uses specialized
# chips on Nvidia video cards.
CODEC = "libx264"

FILENAME = "capture.mp4"


def main() -> None:
    logging.basicConfig(level=logging.DEBUG)
    # If we don't enable PyAV's own logging, a lot of important error messages from libav won't be shown.
    av.logging.set_level(av.logging.VERBOSE)

    with mss.mss() as sct:
        monitor = sct.monitors[1]

        with av.open(FILENAME, "w") as avmux:
            # The "avmux" object we get back from "av.open" represents the MP4 file.  That's a container that holds
            # the video, as well as possibly audio and more.  These are each called "streams".  We only create one
            # stream here, since we're just recording video.
            video_stream = avmux.add_stream(CODEC, rate=FPS, options=CODEC_OPTIONS)
            # Width and height must be divisible by 2, otherwise the encoder will fail.
            # Round down to the nearest even number.
            video_stream.width = monitor["width"] & ~1
            video_stream.height = monitor["height"] & ~1
            # There are more options you can set on the video stream; the full demo uses some of those.

            # Count how many frames we're capturing, so we can log the FPS later.
            frame_count = 0

            # Mark the times when we start and end the recording.
            capture_start_time = time.monotonic()
            capture_end_time = capture_start_time + CAPTURE_SECONDS

            # MSS can capture very fast, and libav can encode very fast, depending on your hardware and screen size.
            # We don't want to capture faster than 30 fps (or whatever you set FPS to).  To slow down to our desired
            # rate, we keep a variable "next_frame_time" to track when it's time to track the next frame.
            #
            # Some programs will just sleep for 1/30 sec in each loop.  But by tracking the time when we want to
            # capture the next frame, instead of always sleeping for 1/30 sec, the time that is spent doing the
            # capture and encode (which can be substantial) is counted as part of the total time we need to delay.
            next_frame_time = capture_start_time

            print("Capturing to", FILENAME, "for", CAPTURE_SECONDS, "seconds")
            while True:
                # Wait until we reach the time for the next frame.
                while (now := time.monotonic()) < next_frame_time:
                    time.sleep(next_frame_time - now)

                # Try to capture the next frame 1/30 sec after our target time for this frame.  We update this based
                # on the target time instead of the actual time so that, if we were a little slow capturing this
                # frame, we'll be a little fast capturing the next one, and even things out.  (There's a slightly
                # better, but more complex, way to update next_frame_time in the full demo.)
                next_frame_time = next_frame_time + 1 / FPS

                # See if we've finished the requested capture duration.
                if now > capture_end_time:
                    break

                # Print dots for each frame, so you know it's not frozen.
                print(".", end="", flush=True)

                # Grab a screenshot.
                screenshot = sct.grab(monitor)
                frame_count += 1

                # There are a few ways to get the screenshot into a VideoFrame.  The highest-performance way isn't
                # hard, and is shown in the full demo: search for from_numpy_buffer.  But the most obvious way is to
                # use PIL: you can create an Image from the screenshot, and create a VideoFrame from that.  That said,
                # if you want to boost the fps rate by about 50%, check out the full demo, and search for
                # from_numpy_buffer.
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                frame = av.VideoFrame.from_image(img)

                # When we encode frames, we get back a list of packets.  Often, we'll get no packets at first: the
                # video encoder wants to wait and see the motion before it decides how it wants to encode the frames.
                # Later, once it's decided about the earlier frames, we'll start getting those packets, while it's
                # holding on to later frames.
                #
                # You can imagine that the encoder is a factory.  You're providing it frames, one at a time, each as a
                # box of raw materials.  It cranks out packets as its finished product.  But there's some delay while
                # it's working.  You can imagine these on a conveyor belt moving left to right as time progresses:
                #
                #   FRAMES       ENCODER      PACKETS
                # [1]________-> (Factory) ->____________
                # [3]_[2]_[1]-> (Factory) ->____________
                # [6]_[5]_[4]-> (Factory) ->{1}_________
                # [8]_[7]_[6]-> (Factory) ->{3}_{2}_{1}_
                #
                # Sometimes, when you send in a frame, you'll get no packets, sometimes you'll get one, and sometimes
                # you'll get a batch of several.  It depends on how the encoder works.
                #
                # The point is, the packets you're getting back from this call are whatever the encoder is ready to
                # give you, not necessarily the packets related to the frame you're handing it right now.
                packets = video_stream.encode(frame)

                # As we said, the MP4 file is a bunch of packets from possibly many streams, all woven (or "muxed")
                # together.  So the ultimate destination of the data is to send it to the MP4 file, avmux.
                avmux.mux(packets)

            # Print an empty line to end our line of dots.
            print()

            # Earlier, we mentioned that the encoder might hold onto some frames, while it decides how to encode them
            # based on future frames.  Now that we're done sending it frames, we need to get the packets for any
            # frames it's still holding onto.  This is referred to as "flushing" the stream.  We do this by sending
            # None instead of a frame object.
            packets = video_stream.encode(None)
            avmux.mux(packets)

    print(f"Capture complete: {frame_count / CAPTURE_SECONDS:.1f} fps")


if __name__ == "__main__":
    main()
