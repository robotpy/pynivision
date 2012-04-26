#
# Image Management functions
#
import ctypes as C
from . import core
from .core import Image, STDFUNC, STDPTRFUNC
from .information import imaqGetImageType

__all__ = ["imaqArrayToImage", "imaqCreateImage", "imaqImageToArray"]

imaqArrayToImage = STDFUNC("imaqArrayToImage", ("image", Image),
        ("array", C.c_void_p), ("numCols", C.c_int), ("numRows", C.c_int))

imaqCreateImage = STDPTRFUNC("imaqCreateImage", Image,
        ("type", core.ImageType), ("borderSize", C.c_int, 0))

_imaqImageToArray = STDPTRFUNC("imaqImageToArray", C.c_void_p,
        ("image", Image), ("rect", core.Rect),
        ("cols", C.POINTER(C.c_int)), ("rows", C.POINTER(C.c_int)))
def imaqImageToArray(image, rect=core.IMAQ_NO_RECT):
    cols = C.c_int()
    rows = C.c_int()
    d = _imaqImageToArray(image, rect, C.byref(cols), C.byref(rows))
    t = imaqGetImageType(image)
    data = C.string_at(d, cols.value*rows.value*core.ImageType_size[t])
    core.imaqDispose(d)
    return data, cols.value, rows.value
