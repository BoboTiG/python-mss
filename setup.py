# coding: utf-8

from setuptools import setup

from mss import __version__


classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Environment :: MacOS X",
    "Environment :: Win32 (MS Windows)",
    "Environment :: X11 Applications",
    "Intended Audience :: Customer Service",
    "Intended Audience :: Developers",
    "Intended Audience :: Information Technology",
    "Intended Audience :: Education",
    "Intended Audience :: End Users/Desktop",
    "Intended Audience :: Financial and Insurance Industry",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Other Audience",
    "Intended Audience :: Science/Research",
    "Intended Audience :: System Administrators",
    "Intended Audience :: Telecommunications Industry",
    "License :: OSI Approved :: MIT License",
    "Natural Language :: English",
    "Operating System :: MacOS",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: OS Independent",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Topic :: Multimedia :: Graphics :: Capture :: Screen Capture",
]

with open("README.rst") as f:
    description = f.read()

config = {
    "name": "mss",
    "version": __version__,
    "author": "Tiger-222",
    "author_email": "contact@tiger-222.fr",
    "maintainer": "Tiger-222",
    "maintainer_email": "contact@tiger-222.fr",
    "url": "https://github.com/BoboTiG/python-mss",
    "description": (
        "An ultra fast cross-platform multiple screenshots module "
        "in pure python using ctypes."
    ),
    "long_description": description,
    "classifiers": classifiers,
    "platforms": ["Darwin", "Linux", "Windows"],
    "packages": ["mss"],
    "entry_points": {"console_scripts": ["mss=mss.__main__:main"]},
    "license": "MIT",
}

setup(**config)
