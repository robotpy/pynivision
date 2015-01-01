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
#def imaqFlatten(image, type, compression, quality):
#    size = ctypes.c_uint()
#    rv = _imaqFlatten(image, type, compression, quality, ctypes.byref(size))
#    return DisposedArray(ctypes.cast(rv, ctypes.POINTER(ctypes.c_byte)), size.value)
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
    labels = ctypes.create_string_buffer(IMAQDX_MAX_API_STRING_LENGTH*numberOfPatterns)
    ctypes.memset(labels, 0, IMAQDX_MAX_API_STRING_LENGTH*numberOfPatterns)
    if len(labels) != numberOfPatterns:
        raise ValueError("len(labels) does not match len(patterns)")
    for i, label in enumerate(labels):
        for j, ch in enumerate(label):
            labels[i*IMAQDX_MAX_API_STRING_LENGTH+j] = ch
    rv = _imaqLearnMultipleGeometricPatterns(patterns, numberOfPatterns, labels)
    return DisposedPointer(rv)

# copyin String255
def imaqReadMultipleGeometricPatternFile(fileName, description):
    description = ctypes.create_string_buffer(description, 256)
    rv = _imaqReadMultipleGeometricPatternFile(fileName, description)
    return DisposedPointer(rv)

# provided string and length
def IMAQdxGetAttributeDescription(id, name):
    description = ctypes.create_string_buffer(IMAQDX_MAX_API_STRING_LENGTH)
    _IMAQdxGetAttributeDescription(id, name, description, IMAQDX_MAX_API_STRING_LENGTH)
    return ctypes.cast(description, ctypes.c_char_p).value.decode("utf-8")

def IMAQdxGetAttributeDisplayName(id, name):
    displayName = ctypes.create_string_buffer(IMAQDX_MAX_API_STRING_LENGTH)
    _IMAQdxGetAttributeDescription(id, name, displayName, IMAQDX_MAX_API_STRING_LENGTH)
    return ctypes.cast(displayName, ctypes.c_char_p).value.decode("utf-8")

# get/set attribute in/out varies with type
def _IMAQdxAttrGetter(id, name, func):
    attrtype = IMAQdxGetAttributeType(id, name)
    if attrtype == IMAQdxAttributeTypeU32:
        value = ctypes.c_uint32()
        func(id, name, IMAQdxValueTypeU32, ctypes.byref(value))
        return value.value
    elif attrtype == IMAQdxAttributeTypeI64:
        value = ctypes.c_int64()
        func(id, name, IMAQdxValueTypeI64, ctypes.byref(value))
        return value.value
    elif attrtype == IMAQdxAttributeTypeF64:
        value = ctypes.c_double()
        func(id, name, IMAQdxValueTypeF64, ctypes.byref(value))
        return value.value
    elif attrtype == IMAQdxAttributeTypeString:
        value = (ctypes.c_char * IMAQDX_MAX_API_STRING_LENGTH)()
        func(id, name, IMAQdxValueTypeString, value)
        return ctypes.cast(value, ctypes.c_char_p).value
    elif attrtype == IMAQdxAttributeTypeEnum:
        value = IMAQdxEnumItem()
        func(id, name, IMAQdxValueTypeEnumItem, ctypes.byref(value))
        return value
    elif attrtype == IMAQdxAttributeTypeBool:
        value = bool32()
        func(id, name, IMAQdxValueTypeBool, ctypes.byref(value))
        return value.value
    else:
        raise TypeError("can't get attribute of type %s" % attrtype)

def IMAQdxGetAttribute(id, name):
    return _IMAQdxAttrGetter(id, name, _IMAQdxGetAttribute)
def IMAQdxGetAttributeMinimum(id, name):
    return _IMAQdxAttrGetter(id, name, _IMAQdxGetAttributeMinimum)
def IMAQdxGetAttributeMaximum(id, name):
    return _IMAQdxAttrGetter(id, name, _IMAQdxGetAttributeMaximum)
def IMAQdxGetAttributeIncrement(id, name):
    return _IMAQdxAttrGetter(id, name, _IMAQdxGetAttributeIncrement)

_IMAQdxSetAttribute_U32 = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", ctypes.c_uint32), library=_dll2)
_IMAQdxSetAttribute_I64 = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", ctypes.c_int64), library=_dll2)
_IMAQdxSetAttribute_F64 = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", ctypes.c_double), library=_dll2)
_IMAQdxSetAttribute_String = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", ctypes.c_char_p), library=_dll2)
_IMAQdxSetAttribute_Enum = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", IMAQdxEnumItem), library=_dll2)
_IMAQdxSetAttribute_Bool = DXFUNC("IMAQdxSetAttribute", ("id", IMAQdxSession), ("name", ctypes.c_char_p), ("type", IMAQdxValueType), ("value", bool32), library=_dll2)

def IMAQdxSetAttribute(id, name, value):
    attrtype = IMAQdxGetAttributeType(id, name)
    if attrtype == IMAQdxAttributeTypeU32:
        _IMAQdxSetAttribute_U32(id, name, IMAQdxValueTypeU32, int(value))
    elif attrtype == IMAQdxAttributeTypeI64:
        _IMAQdxSetAttribute_I64(id, name, IMAQdxValueTypeI64, int(value))
    elif attrtype == IMAQdxAttributeTypeF64:
        _IMAQdxSetAttribute_F64(id, name, IMAQdxValueTypeF64, float(value))
    elif attrtype == IMAQdxAttributeTypeString:
        _IMAQdxSetAttribute_String(id, name, IMAQdxValueTypeString, value)
    elif attrtype == IMAQdxAttributeTypeEnum:
        # also allow just the enum value or string name
        if isinstance(value, int):
            _IMAQdxSetAttribute_U32(id, name, IMAQdxValueTypeU32, value)
        elif isinstance(value, str):
            _IMAQdxSetAttribute_String(id, name, IMAQdxValueTypeString, value.encode('utf-8'))
        elif isinstance(value, bytes):
            _IMAQdxSetAttribute_String(id, name, IMAQdxValueTypeString, value)
        else:
            _IMAQdxSetAttribute_Enum(id, name, IMAQdxValueTypeEnumItem, value)
    elif attrtype == IMAQdxAttributeTypeBool:
        _IMAQdxSetAttribute_Bool(id, name, IMAQdxValueTypeBool, int(value))
    else:
        raise TypeError("can't set attribute of type %s" % attrtype)

# output array passed with inout count: call with NULL to get count.
def IMAQdxEnumerateCameras(connectedOnly):
    count = ctypes.c_uint(0)
    _IMAQdxEnumerateCameras(None, ctypes.byref(count), connectedOnly)
    cameraInformationArray = (IMAQdxCameraInformation*count.value)()
    _IMAQdxEnumerateCameras(cameraInformationArray, ctypes.byref(count), connectedOnly)
    return ImaqArray(cameraInformationArray, count.value)

def IMAQdxEnumerateVideoModes(id):
    count = ctypes.c_uint(0)
    currentMode = ctypes.c_uint()
    _IMAQdxEnumerateVideoModes(id, None, ctypes.byref(count), ctypes.byref(currentMode))
    videoModeArray = (IMAQdxVideoMode*count.value)()
    _IMAQdxEnumerateVideoModes(id, videoModeArray, ctypes.byref(count), ctypes.byref(currentMode))
    return ImaqArray(videoModeArray, count.value), currentMode

def IMAQdxEnumerateAttributes(id, root):
    count = ctypes.c_uint(0)
    _IMAQdxEnumerateAttributes2(id, None, ctypes.byref(count), root)
    attributeInformationArray = (IMAQdxAttributeInformation*count.value)()
    _IMAQdxEnumerateAttributes2(id, attributeInformationArray, ctypes.byref(count), root)
    return ImaqArray(attributeInformationArray, count.value)

def IMAQdxEnumerateAttributeValues(id, name):
    size = ctypes.c_uint(0)
    _IMAQdxEnumerateAttributeValues(id, name, None, ctypes.byref(size))
    valueList = (IMAQdxEnumItem*size.value)()
    _IMAQdxEnumerateAttributeValues(id, name, valueList, ctypes.byref(size))
    return ImaqArray(valueList, size.value)

def IMAQdxEnumerateAttributes2(id, root, visibility):
    count = ctypes.c_uint(0)
    _IMAQdxEnumerateAttributes2(id, None, ctypes.byref(count), root, visibility)
    attributeInformationArray = (IMAQdxAttributeInformation*count.value)()
    _IMAQdxEnumerateAttributes2(id, attributeInformationArray, ctypes.byref(count), root, visibility)
    return ImaqArray(attributeInformationArray, count.value)

def IMAQdxEnumerateAttributes3(id, root, visibility):
    count = ctypes.c_uint(0)
    _IMAQdxEnumerateAttributes3(id, None, ctypes.byref(count), root, visibility)
    attributeInformationArray = (IMAQdxAttributeInformation*count.value)()
    _IMAQdxEnumerateAttributes3(id, attributeInformationArray, ctypes.byref(count), root, visibility)
    return ImaqArray(attributeInformationArray, count.value)

