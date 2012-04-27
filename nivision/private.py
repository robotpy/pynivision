#
# Private functions
#
import ctypes
from . import core
from .core import Image, STDFUNC, imaqArrayToImage, imaqGetImageType

__all__ = ["Priv_ReadJPEGString", "Priv_ReadJPEGString_C"]

# ReadJPEGString: try to use the LabView one first... but currently this isn't
# exported on Windows.
Priv_ReadJPEGString = None
try:
    _Priv_ReadJPEGString_C = STDFUNC("Priv_ReadJPEGString_C", ("image", Image), ("data", ctypes.c_char_p), ("len", ctypes.c_uint))
except AttributeError:
    try:
        _Priv_ReadJPEGString_C = STDFUNC("Priv_ReadJPEGString_C", ("image", Image), ("data", ctypes.c_char_p), ("len", ctypes.c_uint), library=ctypes.windll.nivissvc)
    except AttributeError:
        _Priv_ReadJPEGString_C = None
if _Priv_ReadJPEGString_C is not None:
    def Priv_ReadJPEGString(image, data):
        _Priv_ReadJPEGString_C(image, data, len(data))

# Fall back to GDI+ JPEG decoder
if Priv_ReadJPEGString is None:
    try:
        from . import gdiplus
        def Priv_ReadJPEGString(image, data):
            t = imaqGetImageType(image)
            if t == core.IMAQ_IMAGE_U16:
                pf = gdiplus.PixelFormat16bppGrayScale
            elif t == core.IMAQ_IMAGE_RGB:
                pf = gdiplus.PixelFormat32bppARGB
            elif t == core.IMAQ_IMAGE_RGB_U64:
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
        from PIL import Image as _PILImage
    except ImportError:
        try:
            import Image as _PILImage
        except ImportError:
            _PILImage = None
    if _PILImage is not None:
        import io
        def Priv_ReadJPEGString(image, data):
            im = _PILImage.open(io.BytesIO(data))
            # only works with RGB for now
            if imaqGetImageType(image) != core.IMAQ_IMAGE_RGB:
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
#        from PyQt4 import QtGui as _QtGui
#        if "jpg" in _QtGui.QImageReader.supportedImageFormats():
#            def Priv_ReadJPEGString(image, data):
#                img = _QtGui.QImage.fromData(data, "JPG")
#    except ImportError:
#        pass

if Priv_ReadJPEGString is None:
    def Priv_ReadJPEGString(image, data):
        raise NotImplementedError

# alias for code ported from C
Priv_ReadJPEGString_C = Priv_ReadJPEGString
