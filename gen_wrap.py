import sys
import os
import re
import configparser

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
    def __init__(self, out, config):
        self.out = out
        self.config = config

    def block_comment(self, comment):
        print("#"*78, file=self.out)
        print("# %s" % comment, file=self.out)
        print("#"*78, file=self.out)

    def opaque_struct(self, name):
        print("class %s(Disposed): pass" % name, file=self.out)

    def define(self, name, value, comment):
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
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
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
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
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
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
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
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
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
            return

        try:
            config = self.config[name]
        except KeyError:
            config = self.config['DEFAULT']

        underscored = config.getboolean("underscored", fallback=False)

        # common return cases
        retpointer = config.getboolean("rvdisposed", fallback=False)
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
        sized_params = dict(tuple(y.strip() for y in x.split(':')) for x in
                config.get("arraysize", "").split(',') if x)
        size_params = set(sized_params.values())
        retarraysize = config.get("retarraysize", "").strip()
        if retarraysize:
            size_params.add(retarraysize)
        if size_params:
            custom = True
        if retpointer:
            custom = True
        config_outparams = \
                set(x.strip() for x in config.get("outparams", "").split(','))
        outparams = []
        paramtypes = {}
        if params:
            defaults = dict((y.strip() for y in x.split(':')) for x in
                    config.get("defaults", "").split(',') if x)
            inparams = set(x.strip() for x in
                    config.get("inparams", "").split(','))
            for pname, ptype, arr in params:
                if pname == "void":
                    continue
                ctype = self.c_to_ctype(ptype, arr)
                paramtypes[pname] = (ptype, arr)
                if pname in defaults:
                    paramstr = '("%s", %s, %s)' % (pname, ctype, defaults[pname])
                else:
                    paramstr = '("%s", %s)' % (pname, ctype)
                funcargs.append(paramstr)

                # try to guess output parameters
                if pname in config_outparams or (pname not in inparams
                        and not underscored
                        and not ptype.startswith("const")
                        and ptype[:-1] not in forward_structs
                        and ptype[-1] == "*"):
                    if functype != "STDFUNC" or ptype[:-1] in enums:
                        custom = True
                    outparams.append(pname)

        if not custom and outparams:
            funcargs.append("out=[" + ", ".join('"%s"' % x for x in outparams) + "]")

        print('%s%s = %s(%s)' %
                ("_" if (underscored or custom) else "", name,
                    functype, ", ".join(funcargs)), file=self.out)

        if custom and not underscored:
            # generate list of input parameters
            inparams = []
            for pname, ptype, arr in params:
                if pname in outparams:
                    continue
                if pname in size_params:
                    continue
                inparams.append(pname)

            # function definition
            print("def %s(%s):" % (name, ", ".join(inparams)), file=self.out)
            retparams = []

            # array input parameters
            for pname, sizepname in sized_params.items():
                # get ctype of parameter
                ptype = paramtypes[pname][0][:-1]
                arr = paramtypes[pname][1]
                ctype = self.c_to_ctype(ptype, arr)
                print("    %s, %s = iterableToArray(%s, %s)" % (pname, sizepname, pname, ctype), file=self.out)

            # placeholders for output parameters
            for pname in outparams:
                if pname in sized_params:
                    continue # array input parameter
                # get ctype of parameter
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

            # arguments to ctypes function
            callargs = []
            for pname, ptype, arr in params:
                if pname in outparams and pname not in sized_params:
                    callargs.append("ctypes.byref(%s)" % pname)
                else:
                    callargs.append(pname)

            # call ctypes function
            if functype == "STDFUNC":
                print("    _%s(%s)" % (name, ", ".join(callargs)), file=self.out)
                if retparams:
                    print("    return %s" % ", ".join(retparams), file=self.out)
            else:
                print("    rv = _%s(%s)" % (name, ", ".join(callargs)), file=self.out)

                # Map return value
                retval = None
                if retarraysize:
                    retval = "DisposedArray(rv, %s.value)" % retarraysize
                    try:
                        retparams.remove("%s.value" % retarraysize)
                    except ValueError:
                        print("%s: could not find %s size return value"
                                % retarraysize)
                        pass

                if retval is None:
                    if retpointer:
                        if config.get("rvdisposed", None) == False:
                            retval = "rv.contents"
                        else:
                            retval = "DisposedPointer(rv)"
                    else:
                        retval = "rv"
                print("    return %s" % ", ".join([retval]+retparams),
                        file=self.out)

        defined.add(name)

    def structunion(self, ctype, name, fields):
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
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

def parse_file(emit, f, block_comment_exclude):
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

def generate(srcdir, outpath, configpath=None, nivisionhpath=None):
    # determine the file to open
    # look in the current directory
    if not nivisionhpath:
        if os.path.exists(os.path.join(srcdir, "nivision.h")):
            nivisionhpath = os.path.join(srcdir, "nivision.h")

    if not configpath:
        if os.path.exists(os.path.join(srcdir, "nivision.ini")):
            configpath = os.path.join(srcdir, "nivision.ini")

    # try to get it from the IMAQ Vision directory
    if not nivisionhpath:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\National Instruments\IMAQ Vision\CurrentVersion', access=winreg.KEY_QUERY_VALUE)
            imaqpath = winreg.QueryValueEx(key, 'Path')[0]
            nivisionhpath = os.path.join(imaqpath, "Include", "nivision.h")
        except (ImportError, WindowsError, IndexError):
            pass

    if not configpath:
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\National Instruments\IMAQ Vision\CurrentVersion', access=winreg.KEY_QUERY_VALUE)
            imaqversion = winreg.QueryValueEx(key, 'VersionString')[0]
            configpath = os.path.join(srcdir, "nivision_%s.ini" % imaqversion)
        except (ImportError, WindowsError, IndexError):
            pass

    # could not find it
    if not nivisionhpath:
        print("Could not find nivision.h")
        sys.exit(1)

    if not configpath:
        print("Could not find configuration .ini file")
        sys.exit(1)

    # read config file
    config = configparser.ConfigParser()
    config.read_file(open(configpath))
    block_comment_exclude = set(x.strip() for x in
            config["Block Comment"]["exclude"].splitlines())

    # open input file
    inf = open(nivisionhpath)

    # prescan for undefined structurs
    prescan_file(inf)
    inf.seek(0)

    # generate
    out = open(outpath, "wt")
    for line in open(os.path.join(srcdir, "ctypes_core_prefix.py")):
        print(line, end='', file=out)
    emit = CtypesEmitter(out, config)
    emit.block_comment("Opaque Structures")
    for name in sorted(opaque_structs):
        emit.opaque_struct(name)
    parse_file(emit, inf, block_comment_exclude)
    for line in open(os.path.join(srcdir, "ctypes_core_suffix.py")):
        print(line, end='', file=out)

if __name__ == "__main__":
    configname = None
    fname = None
    # if specified on the command line, prefer that
    if len(sys.argv) >= 2:
        configname = sys.argv[1]
    if len(sys.argv) >= 3:
        fname = sys.argv[2]

    generate("", os.path.join("nivision", "core.py"), configname, fname)
