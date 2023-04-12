#!/usr/bin/env python3

# --- Copyright Disclaimer ---
#
# In order to support PyInstaller with numpy<1.20.0 this file will be
# duplicated for a short period inside PyInstaller's repository [1]. However
# this file is the intellectual property of the NumPy team and is under the
# terms and conditions outlined their repository [2].
#
# .. refs:
#
#   [1] PyInstaller: https://github.com/pyinstaller/pyinstaller/
#   [2] NumPy's license: https://github.com/numpy/numpy/blob/master/LICENSE.txt
#
"""
This hook should collect all binary files and any hidden modules that numpy
needs.

Our (some-what inadequate) docs for writing PyInstaller hooks are kept here:
https://pyinstaller.readthedocs.io/en/stable/hooks.html

PyInstaller has a lot of NumPy users so we'd consider maintaining this hook to
be high priority. Feel free to @mention either bwoodsend or Legorooj on Github
for help keeping it working.
"""

from PyInstaller.utils.hooks import collect_dynamic_libs
from PyInstaller.compat import is_conda, is_pure_conda

# Collect all DLLs inside numpy's installation folder, dump them into built
# app's root.
binaries = collect_dynamic_libs("numpy", ".")

# If using Conda without any non-conda virtual environment manager:
if is_pure_conda:
    # Assume running the NumPy from Conda-forge and collect it's DLLs from the
    # communal Conda bin directory. DLLs from NumPy's dependencies must also be
    # collected to capture MKL, OpenBlas, OpenMP, etc.
    from PyInstaller.utils.hooks import conda_support
    datas = conda_support.collect_dynamic_libs("numpy", dependencies=True)

# Submodules PyInstaller can't detect (probably because they're only imported
# by extension modules which PyInstaller can't read).
hiddenimports = ['numpy.core._dtype_ctypes']
if is_conda:
    hiddenimports.append("six")

# Remove testing and building code and packages which are referenced throughout
# NumPy but aren't really dependencies.
excludedimports = [
    "scipy",
    "pytest",
    "nose",
    "distutils",
    "f2py",
    "setuptools",
    "numpy.f2py",
    "numpy.distutils",
]
