"""
This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss

Example to capture part of the screen of the monitor 2.
"""
import mss
import mss.tools

with mss.mss() as sct:
    # Get information of monitor 2
    monitor_number = 2
    mon = sct.monitors[monitor_number]

    # The screen part to capture
    monitor = {
        "top": mon["top"] + 100,  # 100px from the top
        "left": mon["left"] + 100,  # 100px from the left
        "width": 160,
        "height": 135,
        "mon": monitor_number,
    }
    output = "sct-mon{mon}_{top}x{left}_{width}x{height}.png".format(**monitor)

    # Grab the data
    sct_img = sct.grab(monitor)

    # Save to the picture file
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
    print(output)
