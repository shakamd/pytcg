# pylint: disable=no-name-in-module,import-error
import os
import subprocess
import sys
import shutil
import glob
import tarfile
import multiprocessing
import time

IS_PYTHON2 = sys.version_info < (3, 0)
if IS_PYTHON2:
    from urllib2 import urlopen
else:
    from urllib.request import urlopen

import platform

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
LIB_DIR = os.path.join(PROJECT_DIR, 'pyvex', 'lib')
INCLUDE_DIR = os.path.join(PROJECT_DIR, 'pyvex', 'include')

try:
    from setuptools import setup
    from setuptools import find_packages
    packages = find_packages()
except ImportError:
    from distutils.core import setup
    packages = []
    for root, _, filenames in os.walk(PROJECT_DIR):
        if "__init__.py" in filenames:
            packages.append(root)

from distutils.util import get_platform
from distutils.errors import LibError
from distutils.command.build import build as _build
from distutils.command.sdist import sdist as _sdist

# if sys.platform in ('win32', 'cygwin'):
#     LIBRARY_FILE = 'pyvex.dll'
#     STATIC_LIBRARY_FILE = 'pyvex.lib'
# elif sys.platform == 'darwin':
#     LIBRARY_FILE = "libpyvex.dylib"
#     STATIC_LIBRARY_FILE = 'libpyvex.a'
# else:
#     LIBRARY_FILE = "libpyvex.so"
#     STATIC_LIBRARY_FILE = 'libpyvex.a'


VEX_LIB_NAME = "vex" # can also be vex-amd64-linux
VEX_PATH = os.path.join(PROJECT_DIR, 'libtcg')

def _build_vex():
    e = os.environ.copy()
    e['MULTIARCH'] = '1'
    e['DEBUG'] = '1'

    cmd1 = ['./build.sh']
    for cmd in (cmd1):
        try:
            if subprocess.call(cmd, cwd=VEX_PATH, env=e) == 0:
                break
        except OSError:
            continue
    else:
        raise LibError("Unable to build libtcg.")

# def _shuffle_files():
#     shutil.rmtree(LIB_DIR, ignore_errors=True)
#     shutil.rmtree(INCLUDE_DIR, ignore_errors=True)
#     os.mkdir(LIB_DIR)
#     os.mkdir(INCLUDE_DIR)

#     pyvex_c_dir = os.path.join(PROJECT_DIR, 'pyvex_c')

#     shutil.copy(os.path.join(pyvex_c_dir, LIBRARY_FILE), LIB_DIR)
#     shutil.copy(os.path.join(pyvex_c_dir, STATIC_LIBRARY_FILE), LIB_DIR)
#     shutil.copy(os.path.join(pyvex_c_dir, 'pyvex.h'), INCLUDE_DIR)
#     for f in glob.glob(os.path.join(VEX_PATH, 'pub', '*')):
#         shutil.copy(f, INCLUDE_DIR)

def _clean_bins():
    shutil.rmtree(LIB_DIR, ignore_errors=True)
    shutil.rmtree(INCLUDE_DIR, ignore_errors=True)

def _copy_sources():
    local_vex_path = os.path.join(PROJECT_DIR, 'vex')
    assert local_vex_path != VEX_PATH
    shutil.rmtree(local_vex_path, ignore_errors=True)
    os.mkdir(local_vex_path)

    vex_src = ['LICENSE.GPL', 'LICENSE.README', 'Makefile-gcc', 'Makefile-msvc', 'common.mk', 'pub/*.h', 'priv/*.c', 'priv/*.h', 'auxprogs/*.c']
    for spec in vex_src:
        dest_dir = os.path.join(local_vex_path, os.path.dirname(spec))
        if not os.path.isdir(dest_dir):
            os.mkdir(dest_dir)
        for srcfile in glob.glob(os.path.join(VEX_PATH, spec)):
            shutil.copy(srcfile, dest_dir)

def _build_ffi():
    import gen_cffi
    try:
        gen_cffi.doit()
    except Exception as e:
        print(repr(e))
        raise

class build(_build):
    def run(self):
        self.execute(_build_vex, (), msg="Building libtcg")
        # self.execute(_build_pyvex, (), msg="Building libpyvex")
        # self.execute(_shuffle_files, (), msg="Copying libraries and headers")
        self.execute(_build_ffi, (), msg="Creating CFFI defs file")
        _build.run(self)

class sdist(_sdist):
    def run(self):
        self.execute(_clean_bins, (), msg="Removing binaries")
        self.execute(_copy_sources, (), msg="Copying VEX sources")
        _sdist.run(self)

cmdclass = { 'build': build, 'sdist': sdist }

try:
    from setuptools.command.develop import develop as _develop
    from setuptools.command.bdist_egg import bdist_egg as _bdist_egg
    class develop(_develop):
        def run(self):
            self.execute(_build_vex, (), msg="Building libtcg")
            # self.execute(_build_pyvex, (), msg="Building libpyvex")
            # self.execute(_shuffle_files, (), msg="Copying libraries and headers")
            self.execute(_build_ffi, (), msg="Creating CFFI defs file")
            _develop.run(self)
    cmdclass['develop'] = develop

    class bdist_egg(_bdist_egg):
        def run(self):
            self.run_command('build')
            _bdist_egg.run(self)
    cmdclass['bdist_egg'] = bdist_egg
except ImportError:
    print("Proper 'develop' support unavailable.")

if 'bdist_wheel' in sys.argv and '--plat-name' not in sys.argv:
    sys.argv.append('--plat-name')
    name = get_platform()
    if 'linux' in name:
        # linux_* platform tags are disallowed because the python ecosystem is fubar
        # linux builds should be built in the centos 5 vm for maximum compatibility
        sys.argv.append('manylinux1_' + platform.machine())
    else:
        # https://www.python.org/dev/peps/pep-0425/
        sys.argv.append(name.replace('.', '_').replace('-', '_'))

setup(
    name="pytcg", version='0.0.0.1', description="A Python interface to libtcg and TCG IR",
    url='https://github.com/angr-tcg/pytcg',
    packages=packages,
    cmdclass=cmdclass,
    install_requires=[
        'pycparser',
        'cffi>=1.0.3',
        'archinfo>=7.8.2.21',
        'bitstring',
        'future',
    ],
    setup_requires=[ 'pycparser', 'cffi>=1.0.3' ],
    include_package_data=True,
    package_data={
        'libtcg': ['*']
    }
)