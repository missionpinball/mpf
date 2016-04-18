"""
Script to generate MPF API from source code.

This essentially does what sphinx-apidoc does, except it gives us more
flexibility with doc titles and templates.

This is based on the autobuild.py script in Kivy.
"""

import importlib
import importlib.util
import os
import sys
from collections import OrderedDict

ignore_list = ['tests']
force_in_toc = ['mpf', 'mpf._version']

# check for verbose
VERBOSE = False
for arg in sys.argv:
    if "verbose=" in arg:
        if arg.split("=")[1] == "yes":
            VERBOSE = True

# Directory of doc
base_dir = os.path.dirname(os.path.abspath(__file__))
dest_dir = os.path.join(base_dir, 'mpf')

if VERBOSE:
    print("Base directory:", base_dir)
    print("Dest directory:", dest_dir)


def writefile(file_name, data):
    global dest_dir
    # avoid rewriting the file if its content didn't change
    f = os.path.join(dest_dir, file_name)
    if VERBOSE:
        print('writing file', file_name)
    if os.path.exists(f):
        with open(f) as fd:
            if fd.read() == data:
                return
    h = open(f, 'w')
    h.write(data)
    h.close()

module_list = list()

# import all the mpf modules
for x, y, z in os.walk('../mpf'):
    for f in z:
        if f.endswith('.py') and not f.startswith('_'):
            module_list.append(os.path.join(x, f).replace(os.sep, '.')[3:-3])
            if VERBOSE:
                print('Adding', os.path.join(x, f).replace(os.sep, '.')[3:-3])
        elif f == '__init__.py':
            if VERBOSE:
                print('Adding', x.replace(os.sep, '.')[3:])
            module_list.append(x.replace(os.sep, '.')[3:])

# remove the things we're ignoring
items_to_remove = list()

for mod in module_list:
    for item in ignore_list:
        if item in mod:
            items_to_remove.append(mod)
            continue

for x in items_to_remove:
    module_list.remove(x)

module_list.sort()

for m in module_list:
    if VERBOSE:
        print("Importing", m)
        print('Import Spec', importlib.util.find_spec(m))
    try:
        importlib.import_module(m)
    except ImportError:
        print("ERROR: could not import", m)

l = list()
for x in sys.modules:
    if x.startswith('mpf') and sys.modules[x]:
        if VERBOSE:
            print("Analyzing", x)
        try:
            l.append((x, sys.modules[x],
                  os.path.basename(sys.modules[x].__file__).rsplit('.', 1)[0]))
        except AttributeError:
            print("ERROR:", x)

l.sort()

# Extract packages from modules
packages = []  # high level packages (e.g. folders)
modules = OrderedDict()  # individual modules
api_modules = []  # combo of both
for name, module, filename in l:
    if name in ignore_list:
        continue
    if not any([name.startswith(x) for x in ignore_list]):
        api_modules.append(name)
    if filename == '__init__':
        packages.append(name)
    else:
        if hasattr(module, '__all__'):
            modules[name] = module.__all__
        else:
            modules[name] = [x for x in dir(module) if not x.startswith('__')]

packages.sort()
api_modules.sort()

# Create index
api_index = '''.. include:: ../mpf-index.rst

.. toctree::
   :maxdepth: 1
   :titlesonly:

'''

for package in api_modules:
    api_index += "   %s.rst\n" % package

writefile('index.rst', api_index)

api_contents = '''API Reference
-------------

.. toctree::
   :maxdepth: 1
   :titlesonly:

'''

for package in packages:
    if package.count('.') == 1 or package in force_in_toc:
        api_contents += "   %s </mpf/%s.rst>\n" % (package, package)

writefile('../contents.rst', api_contents)

# Create index for all packages

template = '''$SUMMARY

API
---

.. automodule:: $PACKAGE
   :members:
   :show-inheritance:
   :undoc-members:
   :inherited-members:

.. toctree::
   :maxdepth: 1
   :titlesonly:

'''


def format_module_docstring(docstring, module):

    if not docstring:
        docstring = '''NO SUMMARY ({1})
{0}

Module: ``{1}``

.. todo::

   This module contains no summary. It will be added automatically once we add
   a summary to the actual module file.

'''.format(('=' * (len(module) + 13)), module)

    else:

        lines = docstring.split('\n')

        found = False
        for index, line in enumerate(lines):
            chars = {x for x in line}
            if chars == set('='):
                found = True
                break

        if found:
            lines.insert(index + 1, "\nModule: ``{}``".format(module))

        docstring = '\n'.join(lines)

    return docstring

for package in packages:
    summary = format_module_docstring(sys.modules[package].__doc__, package)

    t = template.replace('$SUMMARY', summary)
    t = t.replace('$PACKAGE', package)

    # search packages
    for subpackage in packages:
        packagemodule = subpackage.rsplit('.', 1)[0]
        if packagemodule != package or len(subpackage.split('.')) <= 2:
            continue
        t += "   %s </mpf/%s.rst>\n" % (subpackage, subpackage)

    # search modules
    m = list(modules.keys())
    # m.sort(key=lambda x: format_module_docstring(sys.modules[x].__doc__, package))
    m.sort()
    for module in m:
        packagemodule = module.rsplit('.', 1)[0]
        if packagemodule != package:
            continue
        t += "   %s </mpf/%s.rst>\n" % (module, module)

    writefile('%s.rst' % package, t)


# Create index for all module
m = list(modules.keys())
m.sort()
refid = 0

for module in m:
    summary = format_module_docstring(sys.modules[module].__doc__, module)

    t = template.replace('$SUMMARY', summary)
    t = t.replace('$PACKAGE', module)

    writefile('%s.rst' % module, t)


print('Auto-generation finished')
