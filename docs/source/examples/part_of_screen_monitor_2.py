"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Example to capture part of the screen of the monitor 2.
"""

import mss
import mss.tools
from mss.models import Region

with mss.MSS() as sct:
    # Get information of monitor 2
    monitor_number = 2
    monitor = sct.monitors[monitor_number]

    # The screen part to capture
    region = Region(
        left=monitor.left + 100,  # 100px from the left
        top=monitor.top + 100,  # 100px from the top
        width=160,
        height=135,
    )
    output = f"sct-mon{monitor_number}_{region.top}x{region.left}_{region.width}x{region.height}.png"

    # Grab the data
    sct_img = sct.grab(region)

    # Save to the picture file
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
    print(output)
