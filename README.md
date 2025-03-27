# Python MSS

[![PyPI version](https://badge.fury.io/py/mss.svg)](https://badge.fury.io/py/mss)
[![Anaconda version](https://anaconda.org/conda-forge/python-mss/badges/version.svg)](https://anaconda.org/conda-forge/python-mss)
[![Tests workflow](https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/BoboTiG/python-mss/actions/workflows/tests.yml)
[![Downloads](https://static.pepy.tech/personalized-badge/mss?period=total&units=international_system&left_color=black&right_color=orange&left_text=Downloads)](https://pepy.tech/project/mss)

> [!TIP]
> Become **my boss** to help me work on this awesome software, and make the world better:
> 
> [![Patreon](https://img.shields.io/badge/Patreon-F96854?style=for-the-badge&logo=patreon&logoColor=white)](https://www.patreon.com/mschoentgen)

```python
from mss import mss

# The simplest use, save a screenshot of the 1st monitor
with mss() as sct:
    sct.shot()
```

An ultra-fast cross-platform multiple screenshots module in pure python using ctypes.

- **Python 3.9+**, PEP8 compliant, no dependency, thread-safe;
- very basic, it will grab one screenshot by monitor or a screenshot of all monitors and save it to a PNG file;
- but you can use PIL and benefit from all its formats (or add yours directly);
- integrate well with Numpy and OpenCV;
- it could be easily embedded into games and other software which require fast and platform optimized methods to grab screenshots (like AI, Computer Vision);
- get the [source code on GitHub](https://github.com/BoboTiG/python-mss);
- learn with a [bunch of examples](https://python-mss.readthedocs.io/examples.html);
- you can [report a bug](https://github.com/BoboTiG/python-mss/issues);
- need some help? Use the tag *python-mss* on [Stack Overflow](https://stackoverflow.com/questions/tagged/python-mss);
- and there is a [complete, and beautiful, documentation](https://python-mss.readthedocs.io) :)
- **MSS** stands for Multiple ScreenShots;


## Installation

You can install it with pip:

```shell
python -m pip install -U --user mss
```

Or you can install it with Conda:

```shell
conda install -c conda-forge python-mss
```
