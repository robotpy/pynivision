"""
nivision package for Python.
"""

__author__  = "Peter Johnson <robotpy@googlegroups.com>"

from . import camera
from .core import *
from .private import *

try:
    from .version import __version__
except ImportError:
    __version__ = 'master'
