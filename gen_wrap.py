import sys
import os
import re

# exclusion list; no code is generated for these
exclude = set([
        # defines
        "IMAQ_IMPORT",
        "IMAQ_FUNC",
        "IMAQ_STDCALL",
        "IMAQ_CALLBACK",
        # error functions
        "imaqClearError",
        "imaqGetErrorText",
        "imaqGetLastError",
        "imaqGetLastErrorFunc",
        "imaqSetError",
        # management functions
        "imaqDispose",
        # Make* functions are faster in native Python
        "imaqMakeAnnulus",
        "imaqMakePoint",
        "imaqMakePointFloat",
        "imaqMakeRect",
        "imaqMakeRotatedRect",
        "imaqMakeRotatedRectFromRect",
        ])

# underscored list; these are private and wrapped by additional Python code
underscored = set([
        "imaqMulticoreOptions",
        "imaqImageToArray",
        "imaqReadCustomData",
        "imaqFlatten",
        "imaqGetLine",
        "imaqComplexPlaneToArray",
        "imaqVerifyPatterns",
        ])

# default parameters
default_params = dict(
        imaqCreateImage=dict(borderSize=0),
        )

# array size parameters (string=name of other arg, None=size of return value)
array_size_params = dict(
        imaqCaliperTool=dict(numEdgePairs=None),
        imaqCircles=dict(numCircles=None),
        imaqDetectCircles=dict(numMatchesReturned=None),
        imaqDetectEllipses=dict(numMatchesReturned=None),
        imaqDetectExtremes=dict(numExtremes=None),
        imaqDetectLines=dict(numMatchesReturned=None),
        imaqDetectRectangles=dict(numMatchesReturned=None),
        imaqEdgeTool2=dict(numEdges=None),
        imaqEdgeTool=dict(numEdges=None),
        imaqEnumerateCustomKeys=dict(size=None),
        imaqExtractCurves=dict(numCurves=None),
        imaqFindCircles=dict(numCircles=None),
        imaqGetFilterNames=dict(numFilters=None),
        imaqGetGeometricFeaturesFromCurves=dict(numFeatures=None),
        imaqGetGeometricTemplateFeatureInfo=dict(numFeatures=None),
        imaqGetParticleInfo=dict(reportCount=None),
        imaqGetPointsOnContour=dict(numSegments=None),
        imaqGetPointsOnLine=dict(numPoints=None),
        imaqInterpolatePoints=dict(interpCount=None),
        imaqLoadImagePopup=dict(numPaths=None),
        imaqMatchColor=dict(numScores=None),
        imaqMatchColorPattern=dict(numMatches=None),
        imaqMatchGeometricPattern2=dict(numMatches=None),
        imaqMatchGeometricPattern3=dict(numMatches=None),
        imaqMatchGeometricPattern=dict(numMatches=None),
        imaqMatchMultipleGeometricPatterns=dict(numMatches=None),
        imaqMatchPattern2=dict(numMatches=None),
        imaqMatchPattern3=dict(numMatches=None),
        imaqMatchPattern=dict(numMatches=None),
        imaqMatchShape=dict(numMatches=None),
        imaqReadDataMatrixBarcode=dict(numBarcodes=None),
        imaqReadPDF417Barcode=dict(numBarcodes=None),
        imaqRefineMatches=dict(numCandidatesOut=None),
        imaqSelectParticles=dict(selectedCount=None),
        imaqSimpleEdge=dict(numEdges=None),
        imaqVerifyText=dict(numScores=None),
        )

# override output parameters
output_params = dict(
        imaqGetWindowBackground=["backgroundColor"],
        )
not_output_params = dict(
        imaqConvolve2=["kernel"],
        imaqExtractTextureFeatures=["waveletBands"],
        imaqExtractWaveletBands=["waveletBands"],
        )

# pointer return value should NOT be disposed
not_disposed_rv = dict(
        )

# block comment exclusion list
block_comment_exclude = set([
        "Includes",
        "Control Defines",
        "Macros",
        "This accomplishes said task.",
        "If using Visual C++, force startup & shutdown code to run.",
        "Error Management functions",
        ])

# parser regular expressions
number_re = re.compile(r'-?[0-9]+')
constant_re = re.compile(r'[A-Z0-9_]+')
define_re = re.compile(r'^#define\s+(?P<name>(IMAQ|ERR)_[A-Z0-9_]+)\s+(?P<value>.*)')
enum_re = re.compile(r'^typedef\s+enum\s+(?P<name>[A-Za-z0-9]+)_enum\s*{')
enum_value_re = re.compile(r'^\s*(?P<name>[A-Z0-9_]+)\s*=\s*(?P<value>-?[0-9A-Fx]+)\s*,?')
struct_re = re.compile(r'^typedef\s+struct\s+(?P<name>[A-Za-z0-9]+)_struct\s*{')
union_re = re.compile(r'^typedef\s+union\s+(?P<name>[A-Za-z0-9]+)_union\s*{')
func_pointer_re = re.compile(r'(?P<restype>[A-Za-z0-9_*]+)\s*\(\s*[A-Za-z0-9_]*[*]\s*(?P<name>[A-Za-z0-9_]+)\s*\)\s*\((?P<params>[^)]*)\)')
static_const_re = re.compile(r'^static\s+const\s+(?P<type>[A-Za-z0-9_]+)\s+(?P<name>[A-Za-z0-9_]+)\s*=\s*(?P<value>[^;]+);')
function_re = re.compile(r'^(IMAQ_FUNC\s+)?(?P<restype>(const\s+)?[A-Za-z0-9_*]+)\s+(IMAQ_STDCALL\s+)?(?P<name>[A-Za-z0-9_]+)\s*\((?P<params>[^)]*)\);')

# defines deferred until after structures
define_after_struct = []
defined = set()
forward_structs = set()
opaque_structs = set()
enums = set()

class CtypesEmitter:
    def __init__(self, out):
        self.out = out

    def block_comment(self, comment):
        print("#"*78, file=self.out)
        print("# %s" % comment, file=self.out)
        print("#"*78, file=self.out)

    def opaque_struct(self, name):
        print("class %s(Disposed): pass" % name, file=self.out)

    def define(self, name, value, comment):
        if name in exclude:
            return
        clean = None
        after_struct = False
        if value == "TRUE":
            clean = "True"
        elif value == "FALSE":
            clean = "False"
        elif name.startswith("IMAQ_INIT_RGB") and value[0] == '{' and value[-1] == '}':
            clean = "RGBValue(%s)" % ' '.join(value[1:-1].strip().split())
            after_struct = True
        elif value.startswith("imaqMake"):
            clean = value[8:]
            after_struct = True
        elif value[0] == '"':
            clean = 'b'+value
        elif number_re.match(value):
            clean = value
        elif constant_re.match(value):
            clean = value
            after_struct = value not in defined

        if clean is None:
            print("Invalid #define: %s" % name)
            return

        if after_struct:
            define_after_struct.append((name, "%s = %s" % (name, clean)))
            return

        print("%s = %s" % (name, clean), file=self.out)
        defined.add(name)

    def text(self, text):
        print(text, file=self.out)

    def static_const(self, name, ctype, value):
        if hasattr(value, "__iter__"):
            print("%s = %s(%s)" % (name, ctype, ", ".join(value)), file=self.out)
        else:
            print("%s = %s" % (name, value), file=self.out)
        defined.add(name)

    def enum(self, name, values):
        if name in exclude:
            return
        print("class %s(Enumeration): pass" % name, file=self.out)
        for vname, value, comment in values:
            if vname.endswith("SIZE_GUARD"):
                continue
            print("%s = %s(%s)" % (vname, name, value), file=self.out)
            defined.add(vname)
        print("", file=self.out)
        defined.add(name)
        enums.add(name)

    ctypes_map = {
            "int": "c_int",
            "char": "c_char",
            "wchar_t": "c_wchar",
            "unsigned char": "c_ubyte",
            "short": "c_short",
            "unsigned short": "c_ushort",
            "int": "c_int",
            "unsigned": "c_uint",
            "unsigned int": "c_uint",
            "long": "c_long",
            "unsigned long": "c_ulong",
            "__int64": "c_longlong",
            "long long": "c_longlong",
            "unsigned __int64": "c_ulonglong",
            "__uint64": "c_ulonglong",
            "unsigned long long": "c_ulonglong",
            "float": "c_float",
            "double": "c_double",
            "long double": "c_longdouble",
            "char *": "c_char_p",
            "char*": "c_char_p",
            "wchar_t *": "c_wchar_p",
            "wchar_t*": "c_wchar_p",
            "void *": "c_void_p",
            "void*": "c_void_p",
            "size_t": "c_size_t",
            }
    def c_to_ctype(self, name, arr):
        if arr:
            arr = '*'+arr
        if name.startswith("const"):
            name = name[5:].strip()
        ctype = self.ctypes_map.get(name, None)
        if ctype is not None:
            return "ctypes." + ctype + arr
        if name == "void":
            return "None"
        # Opaque structures are treated specially
        if name[:-1] in opaque_structs:
            name = name[:-1]
        # handle pointers recursively
        if name[-1] == '*':
            name = "ctypes.POINTER(%s)" % self.c_to_ctype(name[:-1], "")
        return name + arr

    def typedef(self, name, typedef, arr):
        if name in exclude:
            return
        if typedef.startswith("struct"):
            print("class %s(ctypes.Structure): pass" % name, file=self.out)
        elif typedef.startswith("union"):
            print("class %s(ctypes.Union): pass" % name, file=self.out)
        else:
            print("%s = %s" % (name, self.c_to_ctype(typedef, arr)),
                    file=self.out)
        defined.add(name)

    def typedef_function(self, name, restype, params):
        if name in exclude:
            return
        paramstr = ""
        if params:
            paramstr = ", ".join(self.c_to_ctype(ctype, arr) for name, ctype, arr in params if name != 'void')
            if paramstr:
                paramstr = ", " + paramstr
        print("%s = ctypes.CFUNCTYPE(%s%s)" %
                (name, self.c_to_ctype(restype, ""), paramstr), file=self.out)
        defined.add(name)

    def function(self, name, restype, params):
        if name in exclude:
            return

        # common return cases
        retpointer = False
        funcargs = ['"%s"' % name]
        if restype == "int":
            functype = "STDFUNC"
        else:
            if restype[-1] == "*":
                functype = "STDPTRFUNC"
            else:
                functype = "RETFUNC"
            ctype = self.c_to_ctype(restype, "")
            if "POINTER" in ctype:
                retpointer = True
            funcargs.append(ctype)

        custom = False # generate a custom wrapper function?
        size_params = array_size_params.get(name, {})
        size_params_rev = dict((y, x) for x, y in size_params.items())
        if size_params:
            custom = True
        if retpointer:
            custom = True
        outparams = [x for x in output_params.get(name, [])]
        paramtypes = {}
        if params:
            defaults = default_params.get(name, {})
            not_outputs = not_output_params.get(name, set())
            for pname, ptype, arr in params:
                if pname == "void":
                    continue
                ctype = self.c_to_ctype(ptype, arr)
                paramtypes[pname] = (ptype, arr)
                if pname in defaults:
                    paramstr = '("%s", %s, %s)' % (pname, ctype, repr(defaults[pname]))
                else:
                    paramstr = '("%s", %s)' % (pname, ctype)
                funcargs.append(paramstr)

                # try to guess output parameters
                if (pname not in not_outputs
                        and name not in underscored
                        and not ptype.startswith("const")
                        and ptype[:-1] not in forward_structs
                        and ptype[-1] == "*"):
                    if functype != "STDFUNC" or ptype[:-1] in enums:
                        custom = True
                    outparams.append(pname)

        if not custom and outparams:
            funcargs.append("out=[" + ", ".join('"%s"' % x for x in outparams) + "]")

        print('%s%s = %s(%s)' %
                ("_" if (name in underscored or custom) else "", name,
                    functype, ", ".join(funcargs)), file=self.out)

        if custom:
            inparams = [x[0] for x in params if x[0] not in outparams]
            print("def %s(%s):" % (name, ", ".join(inparams)), file=self.out)
            retparams = []
            for pname in outparams:
                ptype = paramtypes[pname][0][:-1]
                arr = paramtypes[pname][1]
                ctype = self.c_to_ctype(ptype, arr)
                if ptype in enums:
                    init = "0"
                else:
                    init = ""
                print("    %s = %s(%s)" % (pname, ctype, init), file=self.out)
                if ptype in enums:
                    retparams.append(pname)
                else:
                    retparams.append("%s.value" % pname)

            callargs = []
            for pname, ptype, arr in params:
                if pname in outparams:
                    callargs.append("ctypes.byref(%s)" % pname)
                else:
                    callargs.append(pname)

            if functype == "STDFUNC":
                print("    _%s(%s)" % (name, ", ".join(callargs)), file=self.out)
                print("    return %s" % ", ".join(retparams), file=self.out)
            else:
                print("    rv = _%s(%s)" % (name, ", ".join(callargs)), file=self.out)

                # Map return value
                retval = None
                if None in size_params_rev:
                    retval = "DisposedArray(rv, %s.value)" % size_params_rev[None]
                    try:
                        retparams.remove("%s.value" % size_params_rev[None])
                    except ValueError:
                        print("%s: could not find %s size return value"
                                % size_params_rev[None])
                        pass

                if retval is None:
                    if retpointer:
                        if name in not_disposed_rv:
                            retval = "rv.contents"
                        else:
                            retval = "DisposedPointer(rv)"
                    else:
                        retval = "rv"
                print("    return %s" % ", ".join([retval]+retparams),
                        file=self.out)

        defined.add(name)

    def structunion(self, ctype, name, fields):
        if name in exclude:
            return
        if name not in defined:
            print("class %s(ctypes.%s): pass" % (name, ctype), file=self.out)
            defined.add(name)
        print("%s._fields_ = [" % name, file=self.out)
        for fname, ftype, arr, comment in fields:
            print('    ("%s", %s),' % (fname, self.c_to_ctype(ftype, arr)),
                    file=self.out)
        print("    ]", file=self.out)

    def struct(self, name, fields):
        self.structunion("Structure", name, fields)

    def union(self, name, fields):
        self.structunion("Union", name, fields)

def parse_cdecl(decl):
    decl = " ".join(decl.split())
    ctype, sep, name = decl.rpartition(' ')
    # look for array[]
    name, bracket, arr = name.partition('[')
    if arr:
        arr = arr[:-1]
    return name, ctype, arr

def split_comment(line):
    if line.startswith('/*'):
        return "", ""
    parts = line.split('//', 1)
    code = parts[0].strip()
    comment = parts[1].strip() if len(parts) > 1 else None
    return code, comment

def prescan_file(f):
    structs = set()

    for line in f:
        code, comment = split_comment(line)
        if not code and not comment:
            continue

        # typedef struct {
        m = struct_re.match(code)
        if m is not None:
            structs.add(m.group('name'))
            continue

        # other typedef
        if code.startswith("typedef"):
            if '(' in code:
                continue
            name, typedef, arr = parse_cdecl(code[8:-1])
            if typedef.startswith("struct"):
                forward_structs.add(name)
            continue

    opaque_structs.update(forward_structs - structs)
    exclude.update(opaque_structs)

def parse_file(emit, f):
    in_block_comment = False
    cur_block = ""
    in_enum = None
    in_struct = None
    in_union = None

    for line in f:
        code, comment = split_comment(line)
        if not code and not comment:
            continue
        #print(comment)

        # in block comment
        if in_block_comment:
            if not code and comment is not None and comment[0] == '=':
                # closing block comment; emit if not excluded
                if cur_block not in block_comment_exclude:
                    emit.block_comment(cur_block)
                in_block_comment = False
                # emit "after struct" constants in Globals
                if cur_block == "Globals":
                    for dname, dtext in define_after_struct:
                        emit.text(dtext)
                        defined.add(dname)
                continue
            if not code and comment is not None:
                # remember current block
                cur_block = comment
            continue

        # inside enum
        if in_enum is not None:
            if code[0] == '}':
                # closing
                emit.enum(*in_enum)
                in_enum = None
                continue
            m = enum_value_re.match(code)
            if m is not None:
                in_enum[1].append((m.group('name'), m.group('value'), comment))
            continue

        # inside struct/union
        if in_struct is not None or in_union is not None:
            if code[0] == '}':
                # closing
                if in_struct is not None:
                    emit.struct(*in_struct)
                    in_struct = None
                if in_union is not None:
                    emit.struct(*in_union)
                    in_union = None
                continue
            name, ctype, arr = parse_cdecl(code[:-1])
            # add to fields
            if in_struct is not None:
                in_struct[1].append((name, ctype, arr, comment))
            if in_union is not None:
                in_union[1].append((name, ctype, arr, comment))
            continue

        # block comment
        if not code and comment is not None and comment[0] == '=':
            in_block_comment = True

        # #define
        m = define_re.match(code)
        if m is not None:
            emit.define(m.group('name'), m.group('value').strip(), comment)
            continue

        # typedef enum {
        m = enum_re.match(code)
        if m is not None:
            in_enum = (m.group('name'), [])
            continue

        # typedef struct {
        m = struct_re.match(code)
        if m is not None:
            in_struct = (m.group('name'), [])
            continue

        # typedef union {
        m = union_re.match(code)
        if m is not None:
            in_union = (m.group('name'), [])
            continue

        # other typedef
        if code.startswith("typedef"):
            # typedef function?
            m = func_pointer_re.match(code[8:-1])
            if m is not None:
                params = [parse_cdecl(param.strip()) for param in m.group('params').strip().split(',') if param.strip()]
                emit.typedef_function(m.group('name'), m.group('restype'), params)
                continue
            if '(' in code:
                print("Invalid typedef: %s" % code)
                continue
            emit.typedef(*parse_cdecl(code[8:-1]))
            continue

        # function
        m = function_re.match(code)
        if m is not None:
            params = [parse_cdecl(param.strip()) for param in m.group('params').strip().split(',') if param.strip()]
            emit.function(m.group('name'), m.group('restype'), params)
            continue

        # static const
        m = static_const_re.match(code)
        if m is not None:
            value = m.group('value')
            if value[0] == '{':
                value = [v.strip() for v in value[1:-1].strip().split(',') if v.strip()]
            emit.static_const(m.group('name'), m.group('type'), value)
            continue

        if not code or code[0] == '#':
            continue

        print("Unrecognized: %s" % code)

def generate(srcdir, outpath, nivisionhpath=None):
    # determine the file to open
    # look in the current directory
    if not nivisionhpath:
        if os.path.exists(os.path.join(srcdir, "nivision.h")):
            nivisionhpath = os.path.join(srcdir, "nivision.h")

    # try to get it from the IMAQ Vision directory
    if not nivisionhpath:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\National Instruments\IMAQ Vision\CurrentVersion', access=winreg.KEY_QUERY_VALUE)
            imaqpath = winreg.QueryValueEx(key, 'Path')[0]
            nivisionhpath = os.path.join(imaqpath, "Include", "nivision.h")
        except (ImportError, WindowsError, IndexError):
            pass

    # could not find it
    if not nivisionhpath:
        print("Could not find nivision.h")
        sys.exit(1)

    # open input file
    inf = open(nivisionhpath)

    # prescan for undefined structurs
    prescan_file(inf)
    inf.seek(0)

    # generate
    out = open(outpath, "wt")
    for line in open(os.path.join(srcdir, "ctypes_core_prefix.py")):
        print(line, end='', file=out)
    emit = CtypesEmitter(out)
    emit.block_comment("Opaque Structures")
    for name in sorted(opaque_structs):
        emit.opaque_struct(name)
    parse_file(emit, inf)
    for line in open(os.path.join(srcdir, "ctypes_core_suffix.py")):
        print(line, end='', file=out)

if __name__ == "__main__":
    fname = None
    # if specified on the command line, prefer that
    if len(sys.argv) > 2:
        fname = sys.argv[1]

    generate("", os.path.join("nivision", "core.py"), fname)
