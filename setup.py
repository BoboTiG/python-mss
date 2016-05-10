from distutils.core import setup

from mss import __version__


# Remove "Legend" and replace icons with text
lines = open('README.rst').readlines()
desc = ''.join(lines[:24] + lines[32:])\
    .replace('\:star:', 'Yes    ')\
    .replace('\:star2:', 'yes     ')\
    .replace('\:question:', '???        ')

setup(
    name='mss',
    version=__version__,
    author='Tiger-222',
    packages=['mss'],
    package_data={'mss': [
        'linux/build.sh',
        'linux/mss.c',
        'linux/32/limss.so',
        'linux/64/libmss.so'
    ]},
    platforms = ['Darwin', 'Linux', 'Windows'],
    license='zlib/libpng',
    author_email='mickael@jmsinfo.co',
    description='An ultra fast cross-platform multiple screenshots module in pure python using ctypes.',
    long_description=desc,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: Customer Service',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Financial and Insurance Industry',
        'Intended Audience :: Healthcare Industry',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: zlib/libpng License',
        'Natural Language :: English',
        'Natural Language :: French',
        'Operating System :: MacOS',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: Microsoft :: Windows :: Windows Vista',
        'Operating System :: Microsoft :: Windows :: Windows XP',
        'Operating System :: OS Independent',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: C',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Games/Entertainment',
        'Topic :: Desktop Environment',
        'Topic :: Multimedia :: Graphics :: Capture',
        'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
        'Topic :: Office/Business',
        'Topic :: Other/Nonlisted Topic',
        'Topic :: Scientific/Engineering',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities'
    ],
    url='https://github.com/BoboTiG/python-mss'
)
