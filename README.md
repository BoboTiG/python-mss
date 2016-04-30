An ultra fast cross-platform multiple screenshots module in pure python using ctypes
===

Very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file, Python 2.6/3.5 compatible & PEP8 compliant.
It could be easily embedded into games and other softwares which require fast and plateforme optimized methods to grab screenshots.

**MSS** stands for **M**ultiple **S**creen**S**hots.

It's under zlib licence.


API change
---

**Warning**: from the version 2.0.0 for specific system import, now you do as:

    # MacOS X
    from mss.darwin import MSS

    # GNU/Linux
    from mss.linux import MSS

    # Microsoft Windows
    from mss.windows import MSS

The second change is the split into several files. Each OS implementation is into a `platform.system()`.py. For GNU/Linux, you will find the `MSS` class into the file "mss/linux.py".

This make life easier for contributors and reviewers.


Installation
---

You can install it with pip:

    pip install --upgrade mss


Support
---

Legend:
* :star: fully functional (latest stable version Python)
* :star2: fully functional (old version Python)
* :question: no machine to test ([reports needed](https://github.com/BoboTiG/python-mss/issues) :smiley:)

Python    | GNU/Linux | MacOS X  | Windows
:---: | :---: | :---: | :---:
**3.5.1** | :star: | :question: | :star:
3.4.4 | :star2: | :question: | :star2:
3.3.6 | :star2: | :question: | :star2:
3.2.6 | :star2: | :question: | :star2:
3.1.5 | :star2: | :question: | :star2:
3.0.1 | :star2: | :question: | :star2:
**2.7.11** | :star: | :star: | :star:
2.6.9 | :star2: | :star2: | :star2:

Feel free to try MSS on a system we had not tested, and let report us by creating an [issue](https://github.com/BoboTiG/python-mss/issues).


Testing
---

You can try the MSS module directly from the console:

    python tests.py


Instance the good class
---

So MSS can be used as simply as:

    from mss import mss
    with mss() as screenshotter:
        # ...

Or import the good one:

    from mss.linux import MSS
    with MSS() as screenshotter:
        # ...

Of course, you can use it the old way:

    from mss import mss  # or from mss.linux import MSS as mss
    screenshotter = mss()
    # ...


Method save(output, mon, callback)
---

For each monitor, grab a screenshot and save it to a file.

Parameters:

    output (str)
        The output filename.
        %d, if present, will be replaced by the monitor number.

    mon (int)
        -1: grab one screenshot of all monitors
         0: grab one screenshot by monitor
         N: grab the screenshot of the monitor N

    callback (def)
        In case where output already exists, call the defined callback
        function with output as parameter.

This is a generator which returns created files.


Examples
---

One screenshot per monitor:

    for filename in screenshotter.save():
        print(filename)

Screenshot of the monitor 1:

    for filename in screenshotter.save(mon=1):
        print(filename)

Screenshot of the monitor 1, with callback:

    def on_exists(fname):
        ''' Callback example when we try to overwrite an existing
            screenshot.
        '''

        from os import rename
        from os.path import isfile

        if isfile(fname):
            newfile = fname + '.old'
            print('{0} -> {1}'.format(fname, newfile))
            rename(fname, newfile)
        return True

    for filename in screenshotter.save(mon=1, callback=on_exists):
        print(filename)

A screenshot to grab them all:

    for filename in screenshotter.save(output='fullscreen-shot.png', mon=-1):
        print(filename)

