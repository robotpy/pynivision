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

# custom to handle c_byte <-> void translation
def imaqFlatten(image, type, compression, quality):
    size = ctypes.c_uint()
    rv = _imaqFlatten(image, type, compression, quality, ctypes.byref(size))
    return DisposedArray(ctypes.cast(rv, ctypes.POINTER(ctypes.c_byte), size.value))
def imaqUnflatten(image, data):
    data, size = iterableToArray(data, ctypes.c_byte)
    _imaqUnflatten(image, data, size)

# type of pointer varies
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
    d = _imaqGetLine(image, start, end, ctypes.byref(numPoints))
    t = _type_to_ctype[imaqGetImageType(image)]
    return DisposedArray(ctypes.cast(d, t), numPoints)

def imaqSetLine(image, array, start, end):
    array, arraySize = iterableToArray(array,
            _type_to_ctype[imaqGetImageType(image)])
    _imaqSetLine(image, array, arraySize, start, end)

def imaqGetPixelAddress(image, pixel):
    d = _imaqGetPixelAddress(image, pixel)
    t = _type_to_ctype[imaqGetImageType(image)]
    return ctypes.cast(d, t)

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

# custom for output parameter array
def imaqReadFile(image, fileName):
    colorTable = (RGBValue*256)()
    numColors = ctypes.c_int()
    _imaqReadFile(image, fileName, colorTable, ctypes.byref(numColors))
    if numColors == 0:
        return []
    return ImaqArray(colorTable, numColors)

# custom for output parameter array
def imaqReadVisionFile(image, fileName):
    colorTable = (RGBValue*256)()
    numColors = ctypes.c_int()
    _imaqReadVisionFile(image, fileName, colorTable, ctypes.byref(numColors))
    if numColors == 0:
        return []
    return ImaqArray(colorTable, numColors)

# number of patterns is for both labels and patterns
def imaqLearnMultipleGeometricPatterns(patterns, labels):
    patterns, numberOfPatterns = iterableToArray(patterns, Image)
    labels = ctypes.create_string_buffer(256*numberOfPatterns)
    ctypes.memset(labels, 0, 256*numberOfPatterns)
    if len(labels) != numberOfPatterns:
        raise ValueError("len(labels) does not match len(patterns)")
    for i, label in enumerate(labels):
        for j, ch in enumerate(label):
            labels[i*256+j] = ch
    rv = _imaqLearnMultipleGeometricPatterns(patterns, numberOfPatterns, labels)
    return DisposedPointer(rv)

# copyin String255
def imaqReadMultipleGeometricPatternFile(fileName, description):
    description = ctypes.create_string_buffer(description, 256)
    rv = _imaqReadMultipleGeometricPatternFile(fileName, description)
    return DisposedPointer(rv)

