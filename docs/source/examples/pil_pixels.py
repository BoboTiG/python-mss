"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

PIL examples to play with pixels.
"""

import mss

with mss.mss() as sct:
    # Get a screenshot of the 1st monitor
    sct_img = sct.grab(sct.monitors[1])

    # Create an Image
    img = sct_img.to_pil("RGB")

    # Set individual pixels (slower)
    pixels = img.load()
    max_x = min(100, sct_img.width)
    max_y = min(100, sct_img.height)
    for x in range(max_x):
        for y in range(max_y):
            r, g, b = pixels[x, y]
            pixels[x, y] = (255 - r, 255 - g, 255 - b)

    # Show it!
    img.show()
