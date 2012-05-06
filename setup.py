#!/usr/bin/env python

import os

from distutils.command.build_py import build_py as _build_py
from distutils.core import setup

from disttest import test

srcdir = os.path.dirname(__file__)

class build_py(_build_py):
    def build_packages(self):
        super().build_packages()
        core_py_path = self.get_module_outfile(self.build_lib, ["nivision"], "core")
        if not os.path.exists(core_py_path):
            import gen_wrap
            gen_wrap.generate(srcdir, core_py_path)

setup(name='pynivision',
      version='1.0',
      description='Python Wrappers for NI Vision',
      author='Peter Johnson',
      author_email='johnson.peter@gmail.com',
      license='BSD',
      url='https://github.com/robotpy/pynivision',
      packages=['nivision'],
      cmdclass={'build_py': build_py, 'test': test},
      options = {
          'test': dict(
              test_type='unittest',
              test_suite='tests.alltests.suite',
              )
          }
      )

