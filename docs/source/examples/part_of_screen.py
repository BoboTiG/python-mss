"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Example to capture part of the screen.
"""

import mss
import mss.tools
from mss.models import Region

with mss.MSS() as sct:
    # The screen part to capture
    region = Region(left=160, top=160, width=160, height=135)
    output = f"sct-{region.top}x{region.left}_{region.width}x{region.height}.png"

    # Grab the data
    sct_img = sct.grab(region)

    # Save to the picture file
    mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
    print(output)
