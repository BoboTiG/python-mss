from time import time
import mss
import mss.tools


def grab(sct):
    monitor = {'top': 144, 'left': 80, 'width': 1397, 'height': 782}
    return sct.grab(monitor)


def access_rgb(sct):
    im = grab(sct)
    return im.rgb


def output(sct, filename=None):
    rgb = access_rgb(sct)
    mss.tools.to_png(rgb, (1397, 782), output=filename)


def save(sct):
    output(sct, filename='screenshot.png')


def benchmark(func):
    count = 0
    start = time()

    with mss.mss() as sct:
        while (time() - start) % 60 < 10:
            count += 1
            func(sct)

    print(func.__name__, count)


benchmark(grab)
benchmark(access_rgb)
benchmark(output)
benchmark(save)
