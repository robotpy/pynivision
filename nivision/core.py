import ctypes as C
import sys

# DLL and function type
if sys.platform.startswith('win'):
    _dll = C.windll.nivision
    _functype = C.WINFUNCTYPE
else:
    _dll = C.cdll.nivision
    _functype = C.CFUNCTYPE

# struct Image wrapper (opaque struct)
class Image(C.c_void_p):
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

def STDFUNC(name, *params, library=_dll, errcheck=_errcheck):
    prototype = _functype(C.c_int, *tuple(param[1] for param in params))
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

def STDPTRFUNC(name, restype, *params, library=_dll, errcheck=_errcheck_ptr):
    prototype = _functype(restype, *tuple(param[1] for param in params))
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
# Error Management functions
#
imaqClearError = STDFUNC("imaqClearError")

_imaqGetErrorText = STDPTRFUNC("imaqGetErrorText", C.c_void_p,
        ("errorCode", C.c_int), errcheck=None)
def imaqGetErrorText(errorCode):
    d = _imaqGetErrorText(errorCode)
    if d is None or d == 0:
        return "Unknown Error."
    s = C.string_at(d)
    imaqDispose(d)
    return str(s, 'utf8')

imaqGetLastError = STDFUNC("imaqGetLastError", errcheck=None)

_imaqGetLastErrorFunc = STDPTRFUNC("imaqGetLastErrorFunc", C.c_char_p,
        errcheck=None)
def imaqGetLastErrorFunc():
    return str(_imaqGetLastErrorFunc(), 'utf8')

_imaqSetError = STDFUNC("imaqSetError", ("errorCode", C.c_int),
        ("function", C.c_char_p), errcheck=None)
def imaqSetError(errorCode, function):
    if isinstance(function, str):
        b = function.encode('utf8')
    else:
        b = function
    return _imaqSetError(errorCode, b)

#
# Memory Management functions
#
_imaqDispose = STDFUNC("imaqDispose", ("object", C.c_void_p))
def imaqDispose(object):
    _imaqDispose(object)
    if hasattr(object, "value"):
        object.value = 0

#
# Enumerated Types
#
class _Enumeration(C.c_uint):
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
        return C.c_uint(obj.value)

class ImageType(_Enumeration): pass
IMAQ_IMAGE_U8      = ImageType(0)
IMAQ_IMAGE_U16     = ImageType(7)
IMAQ_IMAGE_I16     = ImageType(1)
IMAQ_IMAGE_SGL     = ImageType(2)
IMAQ_IMAGE_COMPLEX = ImageType(3)
IMAQ_IMAGE_RGB     = ImageType(4)
IMAQ_IMAGE_HSL     = ImageType(5)
IMAQ_IMAGE_RGB_U64 = ImageType(6)

# mapping from ImageType to byte size for translation functions
ImageType_size = {
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
class Point(C.Structure):
    _fields_ = [("x", C.c_int),
                ("y", C.c_int)]
IMAQ_NO_POINT = Point(-1, -1)

class PointFloat(C.Structure):
    _fields_ = [("x", C.c_float),
                ("y", C.c_float)]
IMAQ_NO_POINT_FLOAT = PointFloat(-1, -1)
IMAQ_NO_OFFSET = PointFloat(0, 0)

class Rect(C.Structure):
    _fields_ = [("top", C.c_int),
                ("left", C.c_int),
                ("height", C.c_int),
                ("width", C.c_int)]
IMAQ_NO_RECT = Rect(0, 0, 0x7FFFFFFF, 0x7FFFFFFF)

class RotatedRect(C.Structure):
    _fields_ = [("top", C.c_int),
                ("left", C.c_int),
                ("height", C.c_int),
                ("width", C.c_int),
                ("angle", C.c_double)]
IMAQ_NO_ROTATED_RECT = RotatedRect(0, 0, 0x7FFFFFFF, 0x7FFFFFFF, 0)

