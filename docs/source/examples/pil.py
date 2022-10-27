"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

PIL example using frombytes().
"""
from PIL import Image

import mss

with mss.mss() as sct:
    # Get rid of the first, as it represents the "All in One" monitor:
    for num, monitor in enumerate(sct.monitors[1:], 1):
        # Get raw pixels from the screen
        sct_img = sct.grab(monitor)

        # Create the Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        # The same, but less efficient:
        # img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)

        # And save it!
        output = f"monitor-{num}.png"
        img.save(output)
        print(output)
