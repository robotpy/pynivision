#
# Image Information functions
#
import ctypes as C
from . import core
from .core import Image, STDFUNC

__all__ = ["imaqGetImageType"]

_imaqGetImageType = STDFUNC("imaqGetImageType", ("image", Image),
        ("type", C.POINTER(core.ImageType)))
def imaqGetImageType(image):
    t = ImageType(0)
    _imaqGetImageType(image, C.byref(t))
    return t
