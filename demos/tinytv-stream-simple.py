#! /usr/bin/env python3

# You're the type of person who likes to understand how things work under the hood.  You want to see a simple example
# of how to stream video to a TinyTV.  This is that example!
#
# There's a more advanced example, tinytv-stream.py, that has more features and better performance.  But this simple
# demo is easier to understand, because it does everything in a straightforward way, without any complicated features.
#
# Wait, what's a TinyTV?  It's a tiny retro-style TV, about 5cm tall.  You can put videos on it, or stream video to it
# over USB.  Advanced users can even reprogram its firmware!  You can find out more about it at https://tinytv.us/
#
# You may want to read at least the docstring at the top of tinytv-stream.py, since it gives you some details about
# setting up permissions on Linux to connect to your TinyTV.
#
# We use three libraries that don't come with Python: PySerial, Pillow, and (of course) MSS.  You'll need to install
# those with "pip install pyserial pillow mss".  Normally, you'll want to install these into a venv; if you don't know
# about those, there are lots of great tutorials online.

from __future__ import annotations

import io
import sys
import time

import serial
from PIL import Image

import mss


def main() -> None:
    # The TinyTV gets streaming input over its USB connection by emulating an old-style serial port.  We can send our
    # video to that serial port, in the format that the TinyTV expects.
    #
    # The advanced demo can find the correct device name by looking at the USB IDs of the devices.  In this simple
    # demo, we just ask the user to supply it.
    if len(sys.argv) != 2:  # noqa: PLR2004
        print(
            f"Usage: {sys.argv[0]} DEVICE\n"
            "where DEVICE is something like /dev/ttyACM0 or COM3.\n"
            'Use "python3 -m serial.tools.list_ports -v" to list your available devices.'
        )
        sys.exit(2)
    device = sys.argv[1]

    # Open the serial port.  It's usually best to use the serial port in a "with:" block like this, to make sure it's
    # cleaned up when you're done with it.
    with serial.Serial(device, timeout=1, write_timeout=1) as ser:
        # The TinyTV might have sent something to the serial port earlier, such as to a program that it was talking to
        # that crashed without reading it.  If that happens, these messages will still be in the device's input
        # buffer, waiting to be read.  We'll just delete anything waiting to be read, to get a fresh start.
        ser.reset_input_buffer()

        # Let's find out what type of TinyTV this is.  The TinyTV has a special command to get that.
        ser.write(b'{"GET":"tvType"}')
        tvtype_response = ser.readline()
        print("Received response:", tvtype_response.strip())

        # The response is usually something like {"tvType":TinyTV2}.  Normally, you'd want to use json.loads to parse
        # JSON.  But this isn't correct JSON (there's no quotes around the TV type), so we can't do that.
        #
        # But we still need to know the TV type, so we can figure out the screen size.  We'll just see if the response
        # mentions the right type.
        if b"TinyTV2" in tvtype_response:
            tinytv_size = (210, 135)
        elif b"TinyTVKit" in tvtype_response:
            tinytv_size = (96, 64)
        elif b"TinyTVMini" in tvtype_response:
            tinytv_size = (64, 64)
        else:
            print("This doesn't seem to be a supported type of TinyTV.")
            sys.exit(1)
        print("Detected TinyTV with screen size", tinytv_size)

        # We're ready to start taking screenshots and sending them to the TinyTV!  Let's start by creating an MSS
        # object.  Like the serial object, we use a "with:" block to make sure that it can clean up after we're done
        # with it.
        #
        # Note that we use the same MSS object the whole time.  We don't try to keep creating a new MSS object each
        # time we take a new screenshot.  That's because the MSS object has a lot of stuff that it sets up and
        # remembers, and creating a new MSS object each time would mean that it has to repeat that setup constantly.
        with mss.mss() as sct:
            # It's time to get the monitor that we're going to capture.  In this demo, we just capture the first
            # monitor.  (We could also use monitors[0] for all the monitors combined.)
            monitor = sct.monitors[1]
            print("Monitor:", monitor)

            # The rest of this will run forever, until we get an error or the user presses Ctrl-C.  Let's record our
            # starting time and count frames, so we can report FPS at the end.
            start_time = time.perf_counter()
            frame_count = 0
            try:
                while True:
                    # First, we get a screenshot.  MSS makes this easy!
                    screenshot = sct.grab(monitor)

                    # The next step is to resize the image to fit the TinyTV's screen.  There's a great image
                    # manipulation library called PIL, or Pillow, that can do that.  Let's transfer the raw pixels in
                    # the ScreenShot object into a PIL Image.
                    original_image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

                    # Now, we can resize it.  The resize method may stretch the image to make it match the TinyTV's
                    # screen; the advanced demo gives other options.  Using a reducing gap is optional, but speeds up
                    # the resize significantly.
                    scaled_image = original_image.resize(tinytv_size, reducing_gap=3.0)

                    # The TinyTV wants its image frames in JPEG format.  PIL can save an image to a JPEG file, but we
                    # want the JPEG data as a bunch of bytes we can transmit to the TinyTV.  Python provides
                    # io.BytesIO to make something that pretends to be a file to PIL, but lets you just get the bytes
                    # that PIL writes.
                    with io.BytesIO() as fh:
                        scaled_image.save(fh, format="JPEG")
                        jpeg_bytes = fh.getvalue()

                    # We're ready to send the frame to the TinyTV!  First, though, this is a good time to look for any
                    # error messages that the TinyTV has sent us.  In today's firmware, anything the TinyTV sends us
                    # is always an error message; it doesn't send us anything normally.  (Of course, this might change
                    # in later firmware versions, so we may need to change this someday.)
                    if ser.in_waiting != 0:
                        # There is indeed an error message.  Let's read it and show it to the user.
                        incoming_data = ser.read(ser.in_waiting)
                        print(f"Error from TinyTV: {incoming_data!r}")
                        sys.exit(1)

                    # The TinyTV wants us to send a command to tell it that we're about to send it a new video frame.
                    # We also need to tell it how many bytes of JPEG data we're going to send.  The command we send
                    # looks like {"FRAME":12345}.
                    delimiter = b'{"FRAME":%i}' % len(jpeg_bytes)
                    ser.write(delimiter)

                    # Now that we've written the command delimiter, we're ready to write the JPEG data.
                    ser.write(jpeg_bytes)

                    # Once we've written the frame, update our counter.
                    frame_count += 1

                    # Now we loop!  This program will keep running forever, or until you press Ctrl-C.

            finally:
                # When the loop exits, report our stats.
                end_time = time.perf_counter()
                run_time = end_time - start_time
                print("Frame count:", frame_count)
                print("Time (secs):", run_time)
                if run_time > 0:
                    print("FPS:", frame_count / run_time)


# Thanks for reading this far!  Let's talk about some improvements; these all appear in the advanced version.
#
# * Right now, the user has to figure out the right device name for the TinyTV's serial port and supply it on the
#   command line.  The advanced version can find the right device automatically by looking at the USB IDs of the
#   connected devices.
#
# * There are a lot of things the user might want to do differently, such as choosing which monitor to capture, or
#   changing the JPEG quality (which can affect how fast the TinyTV can process it).  The advanced version uses
#   argparse to provide command-line options for these things.
#
# * The advanced program shows a status line with things like the current FPS.
#
# * Programs of any significant size have a lot of common things you usually want to think about, like organization
#   into separate functions and classes, error handling, logging, and so forth.  In this simple demo, we didn't worry
#   about those, but they're important for a real program.
#
# * Here's the biggest difference, though.  In the program above, we do a lot of things one at a time.  First we take
#   a screenshot, then we resize it, then we send it to the TinyTV.
#
#   We could overlap these, though: while we're sending one screenshot to the TinyTV, we could be preparing the next
#   one.  This can speed up the program from about 15 fps to about 25 fps, which is about as fast as the TinyTV can
#   run!
#
#   This is called a pipeline.  While it's tough to coordinate, just like it's harder to coordinate a group of people
#   working together than to do everything yourself, it also can be much faster.  A lot of the code in the advanced
#   version is actually about managing the pipeline.
#
#   Using a pipeline isn't always helpful: you have to understand which operations the system can run in parallel, and
#   how Python itself coordinates threads.  That said, I do find that many times, if I'm using MSS to capture video,
#   it does benefit from pipelining these three stages: taking a screenshot, processing it, and sending it somewhere
#   else (like a web server or an AVI file).

if __name__ == "__main__":
    main()
