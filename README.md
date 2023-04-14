# Python MSS

[![PyPI version](https://badge.fury.io/py/mss.svg)](https://badge.fury.io/py/mss)
[![Anaconda version](https://anaconda.org/conda-forge/python-mss/badges/version.svg)](https://anaconda.org/conda-forge/python-mss)
[![Tests workflow](https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml)
[![Downloads](https://static.pepy.tech/personalized-badge/mss?period=total&units=international_system&left_color=black&right_color=orange&left_text=Downloads)](https://pepy.tech/project/mss)

```python
from mss import mss

# The simplest use, save a screen shot of the 1st monitor
with mss() as sct:
    sct.shot()
```

An ultra fast cross-platform multiple screenshots module in pure python using ctypes.

- **Python 3.8+**, PEP8 compliant, no dependency, thread-safe;
- very basic, it will grab one screen shot by monitor or a screen shot of all monitors and save it to a PNG file;
- but you can use PIL and benefit from all its formats (or add yours directly);
- integrate well with Numpy and OpenCV;
- it could be easily embedded into games and other software which require fast and platform optimized methods to grab screen shots (like AI, Computer Vision);
- get the [source code on GitHub](https://github.com/BoboTiG/python-mss);
- learn with a [bunch of examples](https://python-mss.readthedocs.io/examples.html);
- you can [report a bug](https://github.com/BoboTiG/python-mss/issues);
- need some help? Use the tag *python-mss* on [StackOverflow](https://stackoverflow.com/questions/tagged/python-mss);
- and there is a [complete, and beautiful, documentation](https://python-mss.readthedocs.io) :)
- **MSS** stands for Multiple Screen Shots;


## Installation

You can install it with pip:

```shell
python -m pip install -U --user mss
```

Or you can install it with conda:

```shell
conda install -c conda-forge python-mss
```

## Maintenance

For the maintainers, here are commands to upload a new release:

```shell
rm -rf build dist
python -m build
twine check dist/*
twine upload dist/*
```
