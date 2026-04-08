"""This is part of the MSS Python's module.
Source: https://github.com/BoboTiG/python-mss.

Select the XShmGetImage backend explicitly and inspect its status.
"""

from mss import MSS

with MSS(backend="xshmgetimage") as sct:
    screenshot = sct.grab(sct.monitors[1])
    print(f"Captured screenshot dimensions: {screenshot.size.width}x{screenshot.size.height}")

    print("Did MIT-SHM work:")
    for message in sct.performance_status:
        print(message)
