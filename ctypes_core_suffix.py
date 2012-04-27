# native Python versions of these are faster
def imaqMakeAnnulus(center, innerRadius, outerRadius, startAngle, endAngle):
    return Annulus(center, innerRadius, outerRadius, startAngle, endAngle)

def imaqMakePoint(xCoordinate, yCoordinate):
    return Point(xCoordinate, yCoordinate)

def imaqMakePointFloat(xCoordinate, yCoordinate):
    return PointFloat(xCoordinate, yCoordinate)

def imaqMakeRect(top, left, height, width):
    return Rect(top, left, height, width)

def imaqMakeRotatedRect(top, left, height, width, angle):
    return RotatedRect(top, left, height, width, angle)

def imaqMakeRotatedRectFromRect(rect):
    return RotatedRect(rect.top, rect.left, rect.height, rect.width, 0.0)

# custom (for now) for inout parameter
def imaqMulticoreOptions(operation, customNumCores):
    v = ctypes.c_uint(customNumCores)
    _imaqMulticoreOptions(operation, ctypes.byref(v))
    return v.value

# useful imaqMulticoreOptions aliases
def imaqGetCores():
    v = ctypes.c_uint()
    _imaqMulticoreOptions(IMAQ_GET_CORES, ctypes.byref(v))
    return v.value

def imaqSetCores(customNumCores):
    v = ctypes.c_uint(customNumCores)
    _imaqMulticoreOptions(IMAQ_SET_CORES, ctypes.byref(v))

def imaqUseMaxAvailableCores():
    v = ctypes.c_uint()
    _imaqMulticoreOptions(IMAQ_USE_MAX_AVAILABLE, ctypes.byref(v))

# custom (for now) for default parameter
imaqCreateImage = STDPTRFUNC("imaqCreateImage", Image,
        ("type", ImageType), ("borderSize", ctypes.c_int, 0))

# custom to handle data copy
def imaqImageToArray(image, rect=IMAQ_NO_RECT):
    cols = ctypes.c_int()
    rows = ctypes.c_int()
    d = _imaqImageToArray(image, rect, ctypes.byref(cols), ctypes.byref(rows))
    t = imaqGetImageType(image)
    data = ctypes.string_at(d, cols.value*rows.value*imaqGetBytesPerPixel(image))
    imaqDispose(d)
    return data, cols.value, rows.value
