"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

PIL examples to play with pixels.
"""
from PIL import Image

import mss

with mss.mss() as sct:
    # Get a screenshot of the 1st monitor
    sct_img = sct.grab(sct.monitors[1])

    # Create an Image
    img = Image.new("RGB", sct_img.size)

    # Best solution: create a list(tuple(R, G, B), ...) for putdata()
    pixels = zip(sct_img.raw[2::4], sct_img.raw[1::4], sct_img.raw[::4])
    img.putdata(list(pixels))

    # But you can set individual pixels too (slower)
    """
    pixels = img.load()
    for x in range(sct_img.width):
        for y in range(sct_img.height):
            pixels[x, y] = sct_img.pixel(x, y)
    """

    # Show it!
    img.show()
