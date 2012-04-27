import sys
import re

# exclusion list; no code is generated for these
exclude = set([
        # defines
        "IMAQ_IMPORT",
        "IMAQ_FUNC",
        "IMAQ_STDCALL",
        "IMAQ_CALLBACK",
        # structures
        "Image",
        ])

# block comment exclusion list
block_comment_exclude = set([
        "Includes",
        "Control Defines",
        "Macros",
        "This accomplishes said task.",
        "If using Visual C++, force startup & shutdown code to run.",
        ])

# #define name value
number_re = re.compile(r'-?[0-9]+')
constant_re = re.compile(r'[A-Z0-9_]+')
define_re = re.compile(r'^#define (?P<name>(IMAQ|ERR)_[A-Z0-9_]+)\s+(?P<value>[-"{}()a-zA-Z0-9_][-"{}()a-zA-Z0-9_ \t\\,.]*)')
enum_re = re.compile(r'^typedef enum (?P<name>[A-Za-z0-9]+)_enum {')
enum_value_re = re.compile(r'^\s*(?P<name>[A-Z0-9_]+)\s*=\s*(?P<value>-?[0-9A-Fx]+)\s*,?')
struct_re = re.compile(r'^typedef struct (?P<name>[A-Za-z0-9]+)_struct {')
union_re = re.compile(r'^typedef union (?P<name>[A-Za-z0-9]+)_union {')
func_pointer_re = re.compile(r'(?P<restype>[A-Za-z0-9_]+)\s*\(\s*[A-Za-z0-9_]*[*]\s*(?P<name>[A-Za-z0-9_]+)\s*\)\s*\((?P<params>[^)]*)\)')

# defines deferred until after structures
define_after_struct = []
defined = set()

class CtypesEmitter:
    def __init__(self, out):
        self.out = out

    def block_comment(self, comment):
        print("#"*78, file=self.out)
        print("# %s" % comment, file=self.out)
        print("#"*78, file=self.out)

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
            clean = "RGBValue(%s)" % ' '.join(value[1:-1].split())
            after_struct = True
        elif value.startswith("imaqMake"):
            clean = value[8:]
            after_struct = True
        elif value[0] == '"' or number_re.match(value):
            clean = value
        elif constant_re.match(value):
            clean = value
            after_struct = value not in defined

        if clean is None:
            print("Invalid #define: %s" % name)
            return

        if after_struct:
            define_after_struct.append("%s = %s" % (name, clean))
            return

        print("%s = %s" % (name, clean), file=self.out)
        defined.add(name)

    def enum(self, name, values):
        if name in exclude:
            return
        print("class %s(Enumeration): pass" % name, file=self.out)
        for vname, value, comment in values:
            if vname.endswith("SIZE_GUARD"):
                continue
            print("%s = %s(%s)" % (vname, name, value), file=self.out)
        print("", file=self.out)
        defined.add(name)

    ctypes_map = {
            "int": "c_int",
            "char": "c_char",
            "wchar_t": "c_wchar",
            "unsigned char": "c_ubyte",
            "short": "c_short",
            "unsigned short": "c_ushort",
            "int": "c_int",
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
            "void": "None",
            }
    def c_to_ctype(self, name, arr):
        if arr:
            arr = '*'+arr
        ctype = self.ctypes_map.get(name, None)
        if ctype is not None:
            return "ctypes." + ctype + arr
        # Image opaque structure is treated specially
        if name.startswith("Image*") or name.startswith("Image *"):
            name = "Image"
        # handle pointers recursively
        if name[-1] == '*':
            name = "POINTER(%s)" % self.c_to_ctype(name[:-1], "")
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
            paramstr = ", " + ", ".join(self.c_to_ctype(ctype, arr) for name, ctype, arr in params)
        print("%s = CFUNCTYPE(%s%s)" %
                (name, self.c_to_ctype(restype, ""), paramstr), file=self.out)
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

def parse_file(emit, f):
    in_block_comment = False
    cur_block = ""
    in_enum = None
    in_struct = None
    in_union = None
    for line in f.readlines():
        if line.startswith('/*'):
            continue
        parts = line.split('//', 1)
        code = parts[0].strip()
        comment = parts[1].strip() if len(parts) > 1 else None
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
        if in_struct is not None or in_enum is not None:
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
                params = []
                for param in m.group('params').strip().split(','):
                    param = param.strip()
                    if not param:
                        continue
                    params.append(parse_cdecl(param))
                emit.typedef_function(m.group('name'), m.group('restype'), params)
                continue
            if '(' in code:
                print("Invalid typedef: %s" % code)
                continue
            emit.typedef(*parse_cdecl(code[8:-1]))
            continue

if __name__ == "__main__":
    parse_file(CtypesEmitter(open(sys.argv[2], "wt")), open(sys.argv[1]))
