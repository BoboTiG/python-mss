"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Select the XShmGetImage backend explicitly and inspect its status.
"""

from mss.linux.xshmgetimage import MSS as mss

with mss() as sct:
    screenshot = sct.grab(sct.monitors[1])
    print(f"Captured screenshot dimensions: {screenshot.size.width}x{screenshot.size.height}")

    print(f"shm_status: {sct.shm_status.name}")
    if sct.shm_fallback_reason:
        print(f"Falling back to XGetImage because: {sct.shm_fallback_reason}")
    else:
        print("MIT-SHM capture active.")
