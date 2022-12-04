"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Use PIL bbox style and percent values.
"""
import mss
import mss.tools

with mss.mss() as sct:
    # Use the 1st monitor
    monitor = sct.monitors[1]

    # Capture a bbox using percent values
    left = monitor["left"] + monitor["width"] * 5 // 100  # 5% from the left
    top = monitor["top"] + monitor["height"] * 5 // 100  # 5% from the top
    right = left + 400  # 400px width
    lower = top + 400  # 400px height
    bbox = (left, top, right, lower)

    # Grab the picture
    # Using PIL would be something like:
    # im = ImageGrab(bbox=bbox)
    im = sct.grab(bbox)

    # Save it!
    mss.tools.to_png(im.rgb, im.size, output="screenshot.png")
