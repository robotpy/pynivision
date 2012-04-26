from ctypes import *
import io
import sys

# DLL and function type
if sys.platform.startswith('win'):
    dll = windll.nivision
    functype = WINFUNCTYPE
else:
    dll = cdll.nivision
    functype = CFUNCTYPE

# struct Image wrapper (opaque struct)
class Image(c_void_p):
    """An imaq Image."""
    def __del__(self):
        if self.value != 0:
            imaqDispose(self)

#
# Mapping from imaq error codes to Python exceptions
#
class ImaqError(Exception):
    def __init__(self):
        self.code = imaqGetLastError()
        self.func = imaqGetLastErrorFunc()
    def __str__(self):
        if self.func:
            return "%s: %s" % (self.func, imaqGetErrorText(self.code))
        else:
            return "%s" % imaqGetErrorText(self.code)

def _errcheck(result, func, args):
    if result == 0:
        raise ImaqError
    return args

def _errcheck_ptr(result, func, args):
    if (result is None or result == 0 or getattr(result, "value", 1) is None or
            getattr(result, "value", 1) == 0):
        raise ImaqError
    return args

def STDFUNC(name, *params, library=dll, errcheck=_errcheck):
    prototype = functype(c_int, *tuple(param[1] for param in params))
    paramflags = []
    for param in params:
        if len(param) == 3:
            paramflags.append((1, param[0], param[2]))
        else:
            paramflags.append((1, param[0]))
    func = prototype((name, library), tuple(paramflags))
    if errcheck is not None:
        func.errcheck = errcheck
    return func

def STDPTRFUNC(name, restype, *params, library=dll, errcheck=_errcheck_ptr):
    prototype = functype(restype, *tuple(param[1] for param in params))
    paramflags = []
    for param in params:
        if len(param) == 3:
            paramflags.append((1, param[0], param[2]))
        else:
            paramflags.append((1, param[0]))
    func = prototype((name, library), tuple(paramflags))
    if errcheck is not None:
        func.errcheck = errcheck
    return func

#
# Enumerated Types
#
class Enumeration(c_uint):
    def __repr__(self):
        return "%s(%d)" % (self.__class__.__name__, self.value)
    def __eq__(self, other):
        return self.value == other.value
    def __ne__(self, other):
        return self.value != other.value
    def __hash__(self):
        return self.value
    @classmethod
    def from_param(cls, obj):
        if obj.__class__ != cls:
            raise ValueError("Cannot mix enumeration members")
        return c_uint(obj.value)

class ImageType(Enumeration): pass
IMAQ_IMAGE_U8      = ImageType(0)
IMAQ_IMAGE_U16     = ImageType(7)
IMAQ_IMAGE_I16     = ImageType(1)
IMAQ_IMAGE_SGL     = ImageType(2)
IMAQ_IMAGE_COMPLEX = ImageType(3)
IMAQ_IMAGE_RGB     = ImageType(4)
IMAQ_IMAGE_HSL     = ImageType(5)
IMAQ_IMAGE_RGB_U64 = ImageType(6)

# mapping from ImageType to byte size for translation functions
_image_type_size = {
        IMAQ_IMAGE_U8: 1,
        IMAQ_IMAGE_U16: 2,
        IMAQ_IMAGE_I16: 2,
        IMAQ_IMAGE_SGL: 4,
        IMAQ_IMAGE_COMPLEX: 8,
        IMAQ_IMAGE_RGB: 4,
        IMAQ_IMAGE_HSL: 4,
        IMAQ_IMAGE_RGB_U64: 8,
        }

#
# Data Structures
#
class Point(Structure):
    _fields_ = [("x", c_int),
                ("y", c_int)]
IMAQ_NO_POINT = Point(-1, -1)

class PointFloat(Structure):
    _fields_ = [("x", c_float),
                ("y", c_float)]
IMAQ_NO_POINT_FLOAT = PointFloat(-1, -1)
IMAQ_NO_OFFSET = PointFloat(0, 0)

class Rect(Structure):
    _fields_ = [("top", c_int),
                ("left", c_int),
                ("height", c_int),
                ("width", c_int)]
IMAQ_NO_RECT = Rect(0, 0, 0x7FFFFFFF, 0x7FFFFFFF)

class RotatedRect(Structure):
    _fields_ = [("top", c_int),
                ("left", c_int),
                ("height", c_int),
                ("width", c_int),
                ("angle", c_double)]
IMAQ_NO_ROTATED_RECT = RotatedRect(0, 0, 0x7FFFFFFF, 0x7FFFFFFF, 0)

#
# Error Management functions
#
imaqClearError = STDFUNC("imaqClearError")

_imaqGetErrorText = STDPTRFUNC("imaqGetErrorText", c_void_p,
        ("errorCode", c_int), errcheck=None)
def imaqGetErrorText(errorCode):
    d = _imaqGetErrorText(errorCode)
    if d is None or d == 0:
        return "Unknown Error."
    s = string_at(d)
    imaqDispose(d)
    return str(s, 'utf8')

imaqGetLastError = STDFUNC("imaqGetLastError", errcheck=None)

_imaqGetLastErrorFunc = STDPTRFUNC("imaqGetLastErrorFunc", c_char_p,
        errcheck=None)
def imaqGetLastErrorFunc():
    return str(_imaqGetLastErrorFunc(), 'utf8')

_imaqSetError = STDFUNC("imaqSetError", ("errorCode", c_int),
        ("function", c_char_p), errcheck=None)
def imaqSetError(errorCode, function):
    if isinstance(function, str):
        b = function.encode('utf8')
    else:
        b = function
    return _imaqSetError(errorCode, b)

#
# Memory Management functions
#
_imaqDispose = STDFUNC("imaqDispose", ("object", c_void_p))
def imaqDispose(object):
    _imaqDispose(object)
    if hasattr(object, "value"):
        object.value = 0

#
# Image Management functions
#
imaqArrayToImage = STDFUNC("imaqArrayToImage", ("image", Image),
        ("array", c_void_p), ("numCols", c_int), ("numRows", c_int))

imaqCreateImage = STDPTRFUNC("imaqCreateImage", Image, ("type", ImageType),
        ("borderSize", c_int, 0))

_imaqImageToArray = STDPTRFUNC("imaqImageToArray", c_void_p, ("image", Image),
        ("rect", Rect), ("cols", POINTER(c_int)), ("rows", POINTER(c_int)))
def imaqImageToArray(image, rect=IMAQ_NO_RECT):
    cols = c_int()
    rows = c_int()
    d = _imaqImageToArray(image, rect, byref(cols), byref(rows))
    t = imaqGetImageType(image)
    data = string_at(d, cols.value*rows.value*_image_type_size[t])
    imaqDispose(d)
    return data, cols.value, rows.value

#
# Image Information functions
#
_imaqGetImageType = STDFUNC("imaqGetImageType", ("image", Image),
        ("type", POINTER(ImageType)))
def imaqGetImageType(image):
    t = ImageType(0)
    _imaqGetImageType(image, byref(t))
    return t

#
# Utilities functions
#
def imaqMakePoint(xCoordinate, yCoordinate):
    return Point(xCoordinate, yCoordinate)

def imaqMakePointFloat(xCoordinate, yCoordinate):
    return PointFloat(xCoordinate, yCoordinate)

def imaqMakeRect(top, left, height, width):
    return Rect(top, left, height, width)

def imaqMakeRotatedRect(top, left, height, width, angle):
    return RotatedRect(top, left, height, width, angle)

#
# Private functions
#

# ReadJPEGString: try to use the LabView one first... but currently this isn't
# exported on Windows.
Priv_ReadJPEGString = None
try:
    _Priv_ReadJPEGString_C = STDFUNC("Priv_ReadJPEGString_C", ("image", Image), ("data", c_char_p), ("len", c_uint))
except AttributeError:
    try:
        _Priv_ReadJPEGString_C = STDFUNC("Priv_ReadJPEGString_C", ("image", Image), ("data", c_char_p), ("len", c_uint), library=windll.nivissvc)
    except AttributeError:
        _Priv_ReadJPEGString_C = None
if _Priv_ReadJPEGString_C is not None:
    _Priv_ReadJPEGString_C.errcheck = errcheck
    def Priv_ReadJPEGString(image, data):
        _Priv_ReadJPEGString_C(image, data, len(data))

# Fall back to GDI+ JPEG decoder
if Priv_ReadJPEGString is None:
    try:
        from . import gdiplus
        def Priv_ReadJPEGString(image, data):
            t = imaqGetImageType(image)
            if t == IMAQ_IMAGE_U16:
                pf = gdiplus.PixelFormat16bppGrayScale
            elif t == IMAQ_IMAGE_RGB:
                pf = gdiplus.PixelFormat32bppARGB
            elif t == IMAQ_IMAGE_RGB_U64:
                pf = gdiplus.PixelFormat64bppARGB
            else:
                raise ImaqError(-1074396080) # ERR_INVALID_IMAGE_TYPE

            def cb(pixels, cols, rows):
                imaqArrayToImage(image, pixels, cols, rows)
            gdiplus.decode(data, cb, pf)

    except (ImportError, WindowsError, NameError):
        pass

# Fall back to PIL (http://www.lfd.uci.edu/~gohlke/pythonlibs/#pil)
if Priv_ReadJPEGString is None:
    try:
        from PIL import Image as PILImage
    except ImportError:
        try:
            import Image as PILImage
        except ImportError:
            PILImage = None
    if PILImage is not None:
        def Priv_ReadJPEGString(image, data):
            im = PILImage.open(io.BytesIO(data))
            # only works with RGB for now
            if imaqGetImageType(image) != IMAQ_IMAGE_RGB:
                raise ImaqError(-1074396080) # ERR_INVALID_IMAGE_TYPE
            if im.mode == "RGB":
                pixels = im.tobytes("raw", "RGBX")
            elif im.mode == "RGBA":
                pixels = im.tobytes("raw", "RGBA")
            cols, rows = im.size
            imaqArrayToImage(image, pixels, cols, rows)

# Fall back to Qt4
#if Priv_ReadJPEGString is None:
#    try:
#        from PyQt4 import QtGui
#        if "jpg" in QtGui.QImageReader.supportedImageFormats():
#            def Priv_ReadJPEGString(image, data):
#                img = QtGui.QImage.fromData(data, "JPG")
#    except ImportError:
#        pass

if Priv_ReadJPEGString is None:
    def Priv_ReadJPEGString(image, data):
        imaqSetError(1, "Priv_ReadJPEGString")
        raise ImaqError

# alias for code ported from C
Priv_ReadJPEGString_C = Priv_ReadJPEGString

