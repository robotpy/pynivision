#
# Image Information functions
#
import ctypes as C
from . import core
from .core import Image, STDFUNC

class ImageInfo(C.Structure):
    _fields_ = [("imageUnit", core.CalibrationUnit),
                ("stepX", C.c_float),
                ("stepY", C.c_float),
                ("imageType", core.ImageType),
                ("xRes", C.c_int),
                ("yRes", C.c_int),
                ("xOffset", C.c_int),
                ("yOffset", C.c_int),
                ("border", C.c_int),
                ("pixelsPerLine", C.c_int),
                ("reserved0", C.c_void_p),
                ("reserved1", C.c_void_p),
                ("imageStart", C.c_void_p)]

imaqGetBitDepth = STDFUNC("imaqGetBitDepth", ("image", Image),
        ("bitDepth", C.POINTER(C.c_uint)), out=["bitDepth"])
imaqGetBytesPerPixel = STDFUNC("imaqGetBytesPerPixel", ("image", Image),
        ("byteCount", C.POINTER(C.c_int)), out=["byteCount"])
imaqGetImageInfo = STDFUNC("imaqGetImageInfo", ("image", Image),
        ("info", C.POINTER(ImageInfo)), out=["info"])
imaqGetImageSize = STDFUNC("imaqGetImageSize", ("image", Image),
        ("width", C.POINTER(C.c_int)), ("height", C.POINTER(C.c_int)),
        out=["width", "height"])

_imaqGetImageType = STDFUNC("imaqGetImageType", ("image", Image),
        ("type", C.POINTER(core.ImageType)))
def imaqGetImageType(image):
    t = core.ImageType(0)
    _imaqGetImageType(image, C.byref(t))
    return t
