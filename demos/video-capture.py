#! /usr/bin/env python3

from fractions import Fraction
import queue
import threading
import time

import av
import numpy as np
import soundcard as sc
from tqdm.auto import trange

import mss

CODEC_OPTIONS_GLOBAL = {
    "g": "60",              # GOP size: aim for about 2 sec
    "bf": "2",              # enable bframes
    "b": "6M",              # nominal average bitrate target
    "maxrate": "12M",       # peak
    "bufsize": "24M",       # VBV buffer; 1-4 seconds
}

# Some options are, of course, implementation-dependent.  I've
# tried to make these basically similar, but for all I know, they
# might actually produce significantly different output quality.
CODECS = {
    "h264_nvenc": {
        "rc": "vbr",
        "tune": "hq",
        "cq": "23", # quality; similar spirit to CRF, but different
        # The modern presets are the p# ones.  The others are
        # deprecated, often aliases.
        "preset": "p4",  # p1..p7 (higher = slower/better)
        "rc-lookahead": "40",
        "spatial-aq": "1",
        "temporal-aq": "1",
        "b_ref_mode": "1",
    },
    "libx264": {
        # I think that with VBR enabled (as in the global options),
        # libx264 ignores CRF.
        "crf": "23",        # quality; lower=better/larger
        "preset": "medium", # speed/quality trade-off
        "rc-lookahead": "40",
        "aq-mode": "3",
    },
}


def main():
    av.logging.set_level(av.logging.VERBOSE)

    fps = 60
    monitor_id = 1
    duration_secs = 30
    codec = None

    if codec is None:
        for codec in CODECS:
            try:
                # This normalizes the name.
                av.codec.Codec(codec, "w")
                break
            except av.codec.codec.UnknownCodecError:
                pass
        else:
            raise RuntimeError("No viable H.264 codec found")
    else:
        # Normalize the name, for the options lookup.
        codec = av.codec.Codec(codec, "w").name

    mic = sc.get_microphone("loopback")

    with mss.mss() as sct:
        monitor = sct.monitors[monitor_id]

        with av.open("capture.mp4", "w", format="mp4") as avmux:
            time_denom = 90000  # This is a widely-used standard
            time_base = Fraction(1, time_denom)

            audio_stream = avmux.add_stream("opus", options={"b": "64k"})
            audio_stream.time_base = time_base
            # We pre-open the codec, to make sure there's not a warmup frame.
            audio_stream.open()

            options = dict(CODEC_OPTIONS_GLOBAL)
            if codec in CODECS:
                options.update(CODECS[codec])
            video_stream = avmux.add_stream(codec, rate=fps, options=options)
            video_stream.width = monitor["width"]
            video_stream.height = monitor["height"]
            video_stream.time_base = time_base
            if any(f.name == "bgra" for f in video_stream.codec.video_formats):
                video_stream.pix_fmt = "bgra"
            # We pre-open the codec, to make sure there's not a warmup frame.
            video_stream.open()

            def pipeline(q_input, fn, q_output):
                try:
                    while True:
                        try:
                            val_input = q_input.get(timeout=5)
                        except queue.ShutDown:
                            break
                        val_output = fn(val_input)
                        if q_output is not None:
                            q_output.put(val_output, timeout=5)
                finally:
                    q_input.shutdown()
                    if q_output is not None:
                        q_output.shutdown()

            q_audio_preprocess = queue.Queue(1)
            q_audio_encode = queue.Queue(1)
            q_video_preprocess = queue.Queue(1)
            q_video_encode = queue.Queue(1)
            q_mux = queue.Queue(1)

            def video_capture():
                try:
                    next_frame_at = first_frame_at
                    for i in trange(duration_secs * fps):
                        while ((now := time.clock_gettime(time.CLOCK_MONOTONIC)) < next_frame_at):
                            time.sleep(next_frame_at - now)
                        # I think there's an easy way to make this a leaky bucket, but can't quite
                        # think through the math right now.
                        next_frame_at = next_frame_at + 1/fps
                        screenshot = sct.grab(monitor)
                        q_video_preprocess.put((screenshot, now), timeout=5)
                finally:
                    q_video_preprocess.shutdown()

            def video_preprocess(screenshot_and_timestamp):
                (screenshot, timestamp) = screenshot_and_timestamp

                ndarray = np.frombuffer(screenshot.buffer(), dtype=np.uint8)
                ndarray = ndarray.reshape(monitor["height"], monitor["width"], 4)
                # from_numpy_buffer isn't documented. from_ndarray is,
                # but that copies the data.  That's slow enough to
                # slow things down to the point of being a bottleneck!
                frame = av.VideoFrame.from_numpy_buffer(ndarray, format="bgra")

                frame.pts = int((timestamp - first_frame_at) * 90000)
                frame.time_base = Fraction(1, 90000)
                return frame

            video_encode = video_stream.encode

            def audio_preprocess(audio_and_timestamp):
                (audio, timestamp) = audio_and_timestamp
                audio = audio.reshape(1, -1)
                frame = av.AudioFrame.from_ndarray(audio, format='flt', layout='stereo')
                frame.sample_rate = 48000
                frame.pts = int((timestamp - first_frame_at) * 90000)
                frame.time_base = Fraction(1, 90000)
                return frame

            audio_encode = audio_stream.encode

            t_video_capture = threading.Thread(target=video_capture, name="video_capture")
            t_video_preprocess = threading.Thread(target=pipeline, args=(q_video_preprocess, video_preprocess, q_video_encode), name="video_preprocess")
            t_video_encode = threading.Thread(target=pipeline, args=(q_video_encode, video_encode, q_mux), name="video_encode")
            t_audio_preprocess = threading.Thread(target=pipeline, args=(q_audio_preprocess, audio_preprocess, q_audio_encode), name="audio_preprocess")
            t_audio_encode = threading.Thread(target=pipeline, args=(q_audio_encode, audio_encode, q_mux), name="audio_encode")
            t_mux = threading.Thread(target=pipeline, args=(q_mux, avmux.mux, None), name="mux")

            first_frame_at = time.clock_gettime(time.CLOCK_MONOTONIC)
            t_mux.start()
            t_video_encode.start()
            t_video_preprocess.start()
            t_audio_encode.start()
            t_audio_preprocess.start()
            t_video_capture.start()

            print("Capture:   ", t_video_capture.native_id)
            print("Preprocess:", t_video_preprocess.native_id)
            print("Encode:    ", t_video_encode.native_id)
            print("Mux:       ", t_mux.native_id)

            with mic.recorder(samplerate=48000) as audio_recorder:
                while t_video_capture.is_alive():
                    data = audio_recorder.record()
                    now = time.clock_gettime(time.CLOCK_MONOTONIC)
                    timestamp = now - audio_recorder.latency
                    q_audio_preprocess.put((data, timestamp))

            t_video_capture.join()
            t_video_preprocess.join()
            t_video_encode.join()
            t_audio_preprocess.join()
            t_audio_encode.join()
            t_mux.join()

            print(f"Used format {video_stream.format}, "
                  f"reformatter {video_stream.reformatter}")


if __name__ == "__main__":
    main()
