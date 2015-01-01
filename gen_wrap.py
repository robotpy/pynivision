#!/usr/bin/env python3
import sys
import os
import re
import configparser
import codecs

from nivision_parse import *

class CtypesEmitter:
    def __init__(self, srcdir, outdir, config):
        self.srcdir = srcdir
        self.outdir = outdir
        self.config = config

        self.out = open(os.path.join(self.outdir, "core.py"), "wt")
        for line in open(os.path.join(self.srcdir, "ctypes_core_prefix.py")):
            print(line, end='', file=self.out)
        self.block_comment("Opaque Structures")
        for name in sorted(opaque_structs):
            self.opaque_struct(name)

    def finish(self):
        for line in open(os.path.join(self.srcdir, "ctypes_core_suffix.py")):
            print(line, end='', file=self.out)

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
        prev_value = -1
        for vname, value, comment in values:
            if vname.endswith("SIZE_GUARD") or vname.endswith("Guard"):
                continue
            if value is None:
                # auto-increment
                value = "%d" % (prev_value + 1)
            print("%s = %s(%s)" % (vname, name, value), file=self.out)
            defined.add(vname)
            prev_value = int(value, 0)
        print("", file=self.out)
        defined.add(name)
        enums.add(name)

    ctypes_map = {
            "int": "c_int",
            "char": "c_char",
            "wchar_t": "c_wchar",
            "unsigned char": "c_ubyte",
            "short": "c_short",
            "short int": "c_short",
            "unsigned short": "c_ushort",
            "unsigned short int": "c_ushort",
            "int": "c_int",
            "unsigned": "c_uint",
            "unsigned int": "c_uint",
            "long": "c_long",
            "unsigned long": "c_ulong",
            "__int64": "c_longlong",
            "long long": "c_longlong",
            "long long int": "c_longlong",
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
            "uInt8": "c_uint8",
            "uInt16": "c_uint16",
            "uInt32": "c_uint32",
            "uInt64": "c_uint64",
            "Int8": "c_int8",
            "Int16": "c_int16",
            "Int32": "c_int32",
            "Int64": "c_int64",
            "float32": "c_float",
            "float64": "c_double",
            }
    def c_to_ctype(self, name, arr):
        #print(name, arr)
        if arr:
            arr = '*'+arr
        if name.startswith("const"):
            name = name[5:].strip()
        ctype = self.ctypes_map.get(name, None)
        if ctype is not None:
            return "ctypes." + ctype + (arr or "")
        if name == "void":
            return "None"
        # Opaque structures are treated specially
        if name[:-1] in opaque_structs:
            name = name[:-1]
        # handle pointers recursively
        if name[-1] == '*':
            name = "ctypes.POINTER(%s)" % self.c_to_ctype(name[:-1], None)
        if arr == "":
            return "ctypes.POINTER(%s)" % self.c_to_ctype(name, None)
        return name + (arr or "")

    def typedef(self, name, typedef, arr):
        if self.config.getboolean(name, "exclude", fallback=False):
            return
        if name in opaque_structs:
            return
        if typedef.startswith("struct"):
            print("class %s(ctypes.Structure): pass" % name, file=self.out)
        elif typedef.startswith("union"):
            print("class %s(ctypes.Union): pass" % name, file=self.out)
        elif name in self.ctypes_map:
            return
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
                (name, self.c_to_ctype(restype, None), paramstr), file=self.out)
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
        elif restype == "IMAQdxError":
            functype = "DXFUNC"
        else:
            if restype[-1] == "*":
                functype = "STDPTRFUNC"
            else:
                functype = "RETFUNC"
            ctype = self.c_to_ctype(restype, None)
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
                #if name == "IMAQdxEnumerateCameras":
                #    print(pname,ptype,arr,ctype)
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
                    if functype not in ("STDFUNC", "DXFUNC") or ptype[:-1] in enums:
                        custom = True
                    outparams.append(pname)

        if not custom and outparams:
            funcargs.append("out=[" + ", ".join('"%s"' % x for x in outparams) + "]")

        try:
            library = self.config["_platform_"]["library"]
        except KeyError:
            library = "_dll"
        if library != "_dll":
            funcargs.append("library=%s" % library)

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
            if functype in ("STDFUNC", "DXFUNC"):
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

def generate(srcdir, outdir, inputs):
    emit = None

    for fname, configpath in inputs:
        # read config file
        config = configparser.ConfigParser()
        config.read(configpath)
        block_comment_exclude = set(x.strip() for x in
                config["Block Comment"]["exclude"].splitlines())

        # open input file
        with codecs.open(fname, "r", "iso-8859-1") as inf:
            # prescan for undefined structurs
            prescan_file(inf)
            inf.seek(0)

            if emit is None:
                emit = CtypesEmitter(srcdir, outdir, config)
            else:
                emit.config = config

            # generate
            parse_file(emit, inf, block_comment_exclude)

    emit.finish()

if __name__ == "__main__":
    if len(sys.argv) < 3 or ((len(sys.argv)-1) % 2) != 0:
        print("Usage: gen_wrap.py <header.h config.ini>...")
        exit(0)

    inputs = []
    for i in range(1, len(sys.argv), 2):
        fname = sys.argv[i]
        configname = sys.argv[i+1]
        inputs.append((fname, configname))

    generate("", "nivision", inputs)
