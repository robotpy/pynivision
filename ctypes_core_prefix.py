import ctypes
import sys

# DLL and function type
if sys.platform.startswith('win'):
    _dll = ctypes.windll.nivision
    _dll2 = ctypes.windll.niimaqdx
    _functype = ctypes.WINFUNCTYPE
else:
    # XXX: load libstdc++.so.6.0.20 to work around crash loading libHALAthena.
    # This is due to multiple C++ libraries installed on the RoboRIO.
    try:
        _cpp_dll = ctypes.CDLL("/lib/libstdc++.so.6.0.20", mode=ctypes.RTLD_GLOBAL, use_errno=True)
    except OSError:
        pass
    _dll = ctypes.CDLL("libnivision.so")
    _dll2 = ctypes.CDLL("libniimaqdx.so")
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
            return "%s: %s: %s" % (self.func, self.code, imaqGetErrorText(self.code))
        else:
            return "%s: %s" % (self.code, imaqGetErrorText(self.code))

class ImaqDxError(ImaqError):
    def __init__(self, code):
        self.code = code
    def __str__(self):
        return "%s: %s" % (self.code, IMAQdxGetErrorString(self.code))

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

def DXFUNC(name, *params, **kwargs):
    def errcheck(result, func, args):
        if result != 0:
            raise ImaqDxError(result)
        return args

    kwargs.setdefault("errcheck", errcheck)
    return RETFUNC(name, ctypes.c_uint, *params, **kwargs)

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

_IMAQdxGetErrorString = DXFUNC("IMAQdxGetErrorString", ("error", ctypes.c_uint),
        ("message", ctypes.c_char_p), ("messageLength", ctypes.c_uint32),
        errcheck=None, library=_dll2)
def IMAQdxGetErrorString(error):
    message = ctypes.create_string_buffer(256)
    _IMAQdxGetErrorString(error, message, 256)
    return ctypes.cast(message, ctypes.c_char_p).value.decode("utf-8")

#
# Memory Management functions
#
_imaqDispose = STDFUNC("imaqDispose", ("object", ctypes.c_void_p))
def imaqDispose(obj):
    if getattr(obj, "_contents", None) is not None:
        _imaqDispose(ctypes.byref(obj._contents))
        obj._contents = None
    if getattr(obj, "value", None) is not None:
        _imaqDispose(obj)
        obj.value = None

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

#
# Memory Managed Types
#
class Disposed(ctypes.c_void_p):
    __del__ = imaqDispose

class ImaqArray:
    def __init__(self, ptr, length):
        self._contents = ptr
        self._length_ = length

    def __len__(self):
        return self._length_

    def __getitem__(self, key):
        if key < 0 or key > self._length_-1:
            raise IndexError
        return self._contents[key]

    def __setitem__(self, key, value):
        if key < 0 or key > self._length_-1:
            raise IndexError
        self._contents[key] = value

    def __delitem__(self, key):
        if key < 0 or key > self._length_-1:
            raise IndexError
        del self._contents[key] # will raise TypeError, but pass it down anyway

    def __repr__(self):
        return "ImaqArray(%s, %d)" % (self._contents, self._length_)

class DisposedArray(ImaqArray):
    def __repr__(self):
        return "DisposedArray(%s, %d)" % (self._contents, self._length_)

    __del__ = imaqDispose

class DisposedPointer:
    def __init__(self, ptr):
        self._contents = ptr.contents
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_contents"), name)
    def __setattr__(self, name, value):
        if name == "_contents":
            object.__setattr__(self, name, value)
        else:
            setattr(self._contents, name, value)
    def __repr__(self):
        return "DisposedPointer(%s)" % self._contents
    __del__ = imaqDispose

def iterableToArray(param, type):
    """Convert an iterable to a ctypes array of type.
    Returns tuple of array, length."""
    length = getattr(param, "_length_", None)
    if length is None:
        length = len(param)
        arr = (type*length)(*param)
    else:
        arr = param
    return arr, length

