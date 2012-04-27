import ctypes
import sys

# DLL and function type
if sys.platform.startswith('win'):
    _dll = ctypes.windll.nivision
    _functype = ctypes.WINFUNCTYPE
else:
    _dll = ctypes.cdll.nivision
    _functype = ctypes.CFUNCTYPE

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

def RETFUNC(name, restype, *params, out=None, library=_dll,
        errcheck=None, handle_missing=True):
    prototype = _functype(restype, *tuple(param[1] for param in params))
    paramflags = []
    for param in params:
        if out is not None and param[0] in out:
            dir = 2
        else:
            dir = 1
        if len(param) == 3:
            paramflags.append((dir, param[0], param[2]))
        else:
            paramflags.append((dir, param[0]))
    try:
        func = prototype((name, library), tuple(paramflags))
        if errcheck is not None:
            func.errcheck = errcheck
    except AttributeError:
        if not handle_missing:
            raise
        def func(*args, **kwargs):
            raise NotImplementedError
    return func

def STDFUNC(name, *params, **kwargs):
    def errcheck(result, func, args):
        if result == 0:
            raise ImaqError
        return args

    kwargs.setdefault("errcheck", errcheck)
    return RETFUNC(name, ctypes.c_int, *params, **kwargs)

def STDPTRFUNC(name, restype, *params, **kwargs):
    def errcheck(result, func, args):
        if (result is None or result == 0
                or getattr(result, "value", 1) is None
                or getattr(result, "value", 1) == 0):
            raise ImaqError
        return args

    kwargs.setdefault("errcheck", errcheck)
    return RETFUNC(name, restype, *params, **kwargs)

#
# Error Management functions
#
imaqClearError = STDFUNC("imaqClearError")

_imaqGetErrorText = STDPTRFUNC("imaqGetErrorText", ctypes.c_void_p,
        ("errorCode", ctypes.c_int), errcheck=None)
def imaqGetErrorText(errorCode):
    d = _imaqGetErrorText(errorCode)
    if d is None or d == 0:
        return "Unknown Error."
    s = ctypes.string_at(d)
    imaqDispose(d)
    return str(s, 'utf8')

imaqGetLastError = STDFUNC("imaqGetLastError", errcheck=None)

_imaqGetLastErrorFunc = STDPTRFUNC("imaqGetLastErrorFunc", ctypes.c_char_p,
        errcheck=None)
def imaqGetLastErrorFunc():
    return str(_imaqGetLastErrorFunc(), 'utf8')

_imaqSetError = STDFUNC("imaqSetError", ("errorCode", ctypes.c_int),
        ("function", ctypes.c_char_p), errcheck=None)
def imaqSetError(errorCode, function):
    if isinstance(function, str):
        b = function.encode('utf8')
    else:
        b = function
    return _imaqSetError(errorCode, b)

#
# Memory Management functions
#
_imaqDispose = STDFUNC("imaqDispose", ("object", ctypes.c_void_p))
def imaqDispose(object):
    _imaqDispose(object)
    if hasattr(object, "value"):
        object.value = 0

#
# Enumerated Types
#
class Enumeration(ctypes.c_uint):
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
        return ctypes.c_uint(obj.value)

