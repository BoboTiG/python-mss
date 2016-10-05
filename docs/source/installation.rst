============
Installation
============

Recommended way
===============

Quite simple::

    pip install mss


From sources
============

Alternatively, you can get a copy of the module from GitHub::

    git clone https://github.com/BoboTiG/python-mss.git
    cd python-mss


Optional dependency
-------------------

The MSS library is already compiled for 32 and 64 bits architectures but you can build for your system::

    cd mss/linux
    sh build.sh
    cd ../..

The resulting file will be located into ``mss/linux/$ARCH/libmss.so`` and will be used for the next step.


Installation
------------

Install them module::

    sudo python setup.py install

You can avoid the MSS library dependency by specifying the `--no-dependency` argument::

    sudo python setup.py install --no-dependency
