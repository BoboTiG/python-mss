
import sys
from distutils.core import setup
from os import unlink
from platform import architecture, system
from shutil import copyfile as copy
from mss import __version__


with open('MANIFEST.in', 'w') as fileh:
    files = ['include *.rst', 'include doc/*', 'prune test*']
    fileh.write("\n".join(files))

todo = 'check' not in sys.argv and system() == 'Linux'
data_files = []
if todo:
    file_ok = 'libmss.so'
    file_ = 'dep/linux/32/libmss.so'
    if architecture()[0].startswith('64'):
        file_ = 'dep/linux/64/libmss.so'
    copy(file_, file_ok)
    data_files.append(('/usr/lib/', [file_ok]))

setup(
    name='mss',
    version=__version__,
    author='Tiger-222',
    py_modules=['mss'],
    author_email='mickael@jmsinfo.co',
    description='A very fast cross-platform multiple screenshots module in pure python using ctypes',
    long_description=open('README.rst').read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: zlib/libpng License',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: Microsoft :: Windows :: Windows Vista',
        'Operating System :: Microsoft :: Windows :: Windows XP',
        'Operating System :: OS Independent',
        'Operating System :: POSIX :: Linux',
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
        #'Programming Language :: Python :: 3.5',
        'Topic :: Desktop Environment',
        'Topic :: Multimedia :: Graphics :: Capture',
        'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
    ],
    url='https://github.com/BoboTiG/python-mss',
    data_files=data_files
)

if todo and 'install' in sys.argv:
    from subprocess import call
    print('Removing {0}'.format(file_ok))
    unlink(file_ok)
    try:
        print('Removing /etc/ld.so.cache')
        unlink('/etc/ld.so.cache')
        print('Writing /etc/ld.so.cache')
        ret = call(['ldconfig'])
    except OSError:
        pass
