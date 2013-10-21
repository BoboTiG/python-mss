
try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup

open('MANIFEST.in', 'w').write('\n'.join((
    "include *.rst",
)))

from mss import __version__

setup(

    name="mss",
    version=__version__,
    author="Tiger-222",
    py_modules=['mss'],
    author_email="contact@tiger-222.fr",
    description="A cross-platform multi-screen shot module in pure python using ctypes",
    long_description=open('README.rst').read(),
    classifiers=[
        'Programming Language :: Python',
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: zlib/libpng License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Topic :: Multimedia :: Graphics :: Capture :: Screen Capture",
    ],
    url="https://github.com/BoboTiG/python-mss"
)

