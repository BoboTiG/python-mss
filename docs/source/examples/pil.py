# coding: utf-8
"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

PIL example using frombytes().
"""

import mss
from PIL import Image


with mss.mss() as sct:
    # Get rid of the first, as it represents the "All in One" monitor:
    for num, monitor in enumerate(sct.monitors[1:], 1):
        # Get raw pixels from the screen
        sct_img = sct.grab(monitor)

        # Create the Image, solution 1 (slower)
        # img = Image.frombytes('RGB', sct_img.size, sct_img.content)

        # Create the Image, solution 2
        img = Image.frombytes('RGBA', sct_img.size, bytes(sct_img.raw), 'raw', 'BGRA')
        img = img.convert('RGB')  # Convert to RGB
        # img = img.convert('L')  # Or to grayscale

        # And save it!
        output = 'monitor-{0}.png'.format(num)
        img.save(output)
        print(output)
