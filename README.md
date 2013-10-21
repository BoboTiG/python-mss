Python MSS
===

An attempt to create a full functionnal cross-platform multi-screen
shot module in _pure_ python using ctypes.

Very basic, it will grab one screen shot by monitor or a screen shot
of all monitors and save it to an optimised/progressive PNG/JPEG file.

MSS is for *Multi-Screen Shot*.

Dependancies & requirements
---

Python. And that is all :)
MSS is writen in pure python, it uses ctypes.
ctypes has been introduced in Python 2.5, before it will need ctypes modules to be installed separately.

Support
---

|            | GNU/linux | Windows   | Mac OS X  |
|------------|:---------:|:---------:|:---------:|
| python 3.3 | **YES**       | **YES**       | ?         |
| python 3.2 | yes       | yes       | ?         |
| python 3.1 | yes       | yes       | ?         |
| python 3.0 | yes       | yes       | ?         |
| **python 2.7** | **YES**       | **YES**       | **YES**       |
| python 2.6 | yes       | yes       | yes       |

Feel free to try MSS on a system we had not tested, and let report us by creating an [issue](https://github.com/BoboTiG/python-mss/issues).

Usage
---

If you just want to try MSS on your system:

    $ python mss.py


If you want to use MSS on your project, just call a new instance of `MSS*()` and then `save()`.
You can pass `oneshot=True` to create one screen shot of all monitors.

You can determine automatically which class to use:

    from platform import system
    from mss import *

    systems = {
        'Darwin' : MSSMac,
        'Linux'  : MSSLinux,
        'Windows': MSSWindows
    }
    try:
        MSS = systems[system()]
    except KeyError:
        err = 'System "{0}" not implemented.'.format(system())
        raise NotImplementedError(err)

Or simply import the good class:

    from mss import MSSLinux as MSS

Then, it is quite simple:

    try:
        mss = MSS(debug=False)

        # One screen shot per monitor
        for filename in mss.save():
            print('File "{0}" created.'.format(filename))

        # A shot to grab them all :)
        for filename in mss.save(oneshot=True):
            print('File "{0}" created.'.format(filename))
    except Exception as ex:
        print(ex)
        raise

Bonus
---

Just for fun ...
Show us your screen shot with all monitors in one file, we will update the [gallery](https://tiger-222.fr/tout/python-mss/galerie/) ;)


Errors
---

If you access a computer using SSH, do not forget to enable X11 forwarding, option `-X`. Else you will end on a segfault.
