#!/usr/bin/env python

def suite():
    import os
    import unittest

    def my_import(name):
        # See http://docs.python.org/lib/built-in-funcs.html#l2h-6
        components = name.split('.')
        try:
            # python setup.py test
            mod = __import__(name)
            for comp in components[1:]:
                mod = getattr(mod, comp)
        except ImportError:
            # python tests/alltests.py
            mod = __import__(components[1])
        return mod

    modules_to_test = [
        'tests.test_dispose',
        ]
    alltests = unittest.TestSuite()
    for module in map(my_import, modules_to_test):
        alltests.addTest(module.suite())
    return alltests

def dump_garbage():
    import gc
    print('\nGarbage:')
    gc.collect()
    if len(gc.garbage):

        print('\nLeaked objects:')
        for x in gc.garbage:
            s = str(x)
            if len(s) > 77: s = s[:73]+'...'
            print(type(x), '\n  ', s)

        print('There were %d leaks.' % len(gc.garbage))
    else:
        print('Python garbage collector did not detect any leaks.')
        print('However, it is still possible there are leaks in the C code.')

def runall(report_leaks=0):
    report_leaks = report_leaks

    if report_leaks:
        import gc
        gc.enable()
        gc.set_debug(gc.DEBUG_LEAK & ~gc.DEBUG_SAVEALL)

    import os, unittest

    if report_leaks:
        dump_garbage()


if __name__ == '__main__':
    runall(1)
