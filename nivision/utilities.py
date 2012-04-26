#
# Utilities functions
#
import ctypes as C
from . import core
from .core import STDFUNC, STDPTRFUNC, RETFUNC

class KernelFamily(core.Enumeration): pass
IMAQ_GRADIENT_FAMILY  = KernelFamily(0)
IMAQ_LAPLACIAN_FAMILY = KernelFamily(1)
IMAQ_SMOOTHING_FAMILY = KernelFamily(2)
IMAQ_GAUSSIAN_FAMILY  = KernelFamily(3)

class MulticoreOperation(core.Enumeration): pass
IMAQ_GET_CORES          = MulticoreOperation(0)
IMAQ_SET_CORES          = MulticoreOperation(1)
IMAQ_USE_MAX_AVAILABLE  = MulticoreOperation(2)

imaqGetKernel = STDPTRFUNC("imaqGetKernel", C.POINTER(C.c_float),
        ("family", KernelFamily), ("size", C.c_int), ("number", C.c_int))

def imaqMakeAnnulus(center, innerRadius, outerRadius, startAngle, endAngle):
    return core.Annulus(center, innerRadius, outerRadius, startAngle, endAngle)

def imaqMakePoint(xCoordinate, yCoordinate):
    return core.Point(xCoordinate, yCoordinate)

def imaqMakePointFloat(xCoordinate, yCoordinate):
    return core.PointFloat(xCoordinate, yCoordinate)

def imaqMakeRect(top, left, height, width):
    return core.Rect(top, left, height, width)

imaqMakeRectFromRotatedRect = RETFUNC("imaqMakeRectFromRotatedRect", core.Rect,
        ("rotatedRect", core.RotatedRect))

def imaqMakeRotatedRect(top, left, height, width, angle):
    return core.RotatedRect(top, left, height, width, angle)

def imaqMakeRotatedRectFromRect(rect):
    return core.RotatedRect(rect.top, rect.left, rect.height, rect.width, 0.0)

_imaqMulticoreOptions = STDFUNC("imaqMulticoreOptions", ("operation", MulticoreOperation), ("customNumCores", C.POINTER(C.c_uint)))
def imaqMulticoreOptions(operation, customNumCores):
    v = C.c_uint(customNumCores)
    _imaqMulticoreOptions(operation, C.byref(v))
    return v.value

def imaqGetCores():
    v = C.c_uint()
    _imaqMulticoreOptions(IMAQ_GET_CORES, C.byref(v))
    return v.value

def imaqSetCores(customNumCores):
    v = C.c_uint(customNumCores)
    _imaqMulticoreOptions(IMAQ_SET_CORES, C.byref(v))

def imaqUseMaxAvailableCores():
    v = C.c_uint()
    _imaqMulticoreOptions(IMAQ_USE_MAX_AVAILABLE, C.byref(v))
