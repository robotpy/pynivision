from ctypes import *
from ctypes.wintypes import BOOL, HGLOBAL

ole32 = windll.ole32
kernel32 = windll.kernel32
gdiplus = windll.gdiplus
mapi32 = windll.mapi32

LPSTREAM = c_void_p
REAL = c_float

GMEM_MOVEABLE = 2

PixelFormat1bppIndexed    = 196865
PixelFormat4bppIndexed    = 197634
PixelFormat8bppIndexed    = 198659
PixelFormat16bppGrayScale = 1052676
PixelFormat16bppRGB555    = 135173
PixelFormat16bppRGB565    = 135174
PixelFormat16bppARGB1555  = 397319
PixelFormat24bppRGB       = 137224
PixelFormat32bppRGB       = 139273
PixelFormat32bppARGB      = 2498570
PixelFormat32bppPARGB     = 925707
PixelFormat48bppRGB       = 1060876
PixelFormat64bppARGB      = 3424269
PixelFormat64bppPARGB     = 29622286
PixelFormatMax            = 15

ImageLockModeRead = 1
ImageLockModeWrite = 2
ImageLockModeUserInputBuf = 4

class GdiplusStartupInput(Structure):
    _fields_ = [
        ('GdiplusVersion', c_uint32),
        ('DebugEventCallback', c_void_p),
        ('SuppressBackgroundThread', BOOL),
        ('SuppressExternalCodecs', BOOL)
    ]

class GdiplusStartupOutput(Structure):
    _fields = [
        ('NotificationHookProc', c_void_p),
        ('NotificationUnhookProc', c_void_p)
    ]

class BitmapData(Structure):
    _fields_ = [
        ('Width', c_uint),
        ('Height', c_uint),
        ('Stride', c_int),
        ('PixelFormat', c_int),
        ('Scan0', POINTER(c_byte)),
        ('Reserved', POINTER(c_uint))
    ]

class Rect(Structure):
    _fields_ = [
        ('X', c_int),
        ('Y', c_int),
        ('Width', c_int),
        ('Height', c_int)
    ]

prototype = WINFUNCTYPE(c_ulong)
IUnknownRelease = prototype(2, "Release")

kernel32.GlobalAlloc.restype = HGLOBAL
kernel32.GlobalLock.restype = c_void_p

def decode(data, cb, pf):
    # Create a HGLOBAL with image data
    hglob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    ptr = kernel32.GlobalLock(hglob)
    memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(hglob)

    # Create IStream for the HGLOBAL
    stream = LPSTREAM()
    ole32.CreateStreamOnHGlobal(hglob, True, byref(stream))

    # Load image from stream
    bitmap = c_void_p()
    status = gdiplus.GdipCreateBitmapFromStream(stream, byref(bitmap))
    if status != 0:
        IUnknownRelease(stream)
        raise ValueError('GDI+ cannot load image')

    # Get size of image (Bitmap subclasses Image)
    width = REAL()
    height = REAL()
    gdiplus.GdipGetImageDimension(bitmap, byref(width), byref(height))
    width = int(width.value)
    height = int(height.value)

    # Get image pixel format
    #pf = c_int()
    #gdiplus.GdipGetImagePixelFormat(bitmap, byref(pf))
    #pf = pf.value

    # Lock pixel data
    rect = Rect()
    rect.X = 0
    rect.Y = 0
    rect.Width = width
    rect.Height = height
    bitmap_data = BitmapData()
    gdiplus.GdipBitmapLockBits(bitmap,
        byref(rect), ImageLockModeRead, pf, byref(bitmap_data))

    # Callback
    try:
        cb(bitmap_data.Scan0, width, height)
    finally:
        # Unlock data
        gdiplus.GdipBitmapUnlockBits(bitmap, byref(bitmap_data))

        # Release image and stream
        gdiplus.GdipDisposeImage(bitmap)
        IUnknownRelease(stream)

_token = c_ulong()
def init():
    startup_in = GdiplusStartupInput()
    startup_in.GdiplusVersion = 1
    startup_out = GdiplusStartupOutput()
    gdiplus.GdiplusStartup(byref(_token), byref(startup_in), byref(startup_out))
init()

import atexit
@atexit.register
def shutdown():
    gdiplus.GdiplusShutdown(_token)

