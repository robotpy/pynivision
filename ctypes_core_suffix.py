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

# custom to handle data size variance and data copy
def imaqImageToArray(image, rect=IMAQ_NO_RECT):
    cols = ctypes.c_int()
    rows = ctypes.c_int()
    d = _imaqImageToArray(image, rect, ctypes.byref(cols), ctypes.byref(rows))
    t = imaqGetImageType(image)
    data = ctypes.string_at(d, cols.value*rows.value*imaqGetBytesPerPixel(image))
    imaqDispose(d)
    return data, cols.value, rows.value

# custom to handle data copy
def imaqReadCustomData(image, key):
    size = ctypes.c_uint()
    d = _imaqReadCustomData(image, key, ctypes.byref(size))
    data = ctypes.string_at(d, size.value)
    imaqDispose(d)
    return data

# custom to handle data copy
def imaqFlatten(image, type, compression, quality):
    size = ctypes.c_uint()
    d = _imaqFlatten(image, type, compression, quality, ctypes.byref(size))
    data = ctypes.string_at(d, size.value)
    imaqDispose(d)
    return data

# type of returned pointer varies
_type_to_ctype = {
        IMAQ_IMAGE_U8: ctypes.c_byte,
        IMAQ_IMAGE_U16: ctypes.c_ushort,
        IMAQ_IMAGE_I16: ctypes.c_short,
        IMAQ_IMAGE_SGL: ctypes.c_float,
        IMAQ_IMAGE_COMPLEX: Complex,
        IMAQ_IMAGE_RGB: RGBValue,
        IMAQ_IMAGE_HSL: HSLValue,
        IMAQ_IMAGE_RGB_U64: RGBU64Value,
        }
def imaqGetLine(image, start, end):
    numPoints = ctypes.c_int()
    d = _imaqFlatten(image, start, end, ctypes.byref(numPoints))
    t = _type_to_ctype[imaqGetImageType(image)]
    return DisposedArray(ctypes.cast(d, t), numPoints)

# custom to handle rows*columns math
# XXX: should this try to build a 2D array (e.g. with numpy) instead?
def imaqComplexPlaneToArray(image, plane, rect):
    rows = ctypes.c_int()
    columns = ctypes.c_int()
    rv = _imaqComplexPlaneToArray(image, plane, rect, ctypes.byref(rows), ctypes.byref(columns))
    return DisposedArray(rv, rows.value*columns.value), rows.value, columns.value

# custom to copyin expectedPatterns to String255
def imaqVerifyPatterns(image, set, expectedPatterns, roi):
    numScores = ctypes.c_int()
    pat = ctypes.create_string_buffer(expectedPatterns, 256)
    rv = _imaqVerifyPatterns(image, set, pat, len(expectedPatterns), roi, ctypes.byref(numScores))
    return DisposedArray(rv, numScores.value)

