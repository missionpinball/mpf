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
from glob import glob

ignore_list = list()

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

# examples_framework_dir = os.path.join(base_dir, '..', 'examples', 'framework')


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
        if f.endswith('.py') and 'tests' not in x and not f.startswith('_'):
            module_list.append(os.path.join(x, f).replace(os.sep, '.')[3:-3])
            if VERBOSE:
                print('Adding', os.path.join(x, f).replace(os.sep, '.')[3:-3])
        elif f == '__init__.py':
            if VERBOSE:
                print('Adding', x.replace(os.sep, '.')[3:])
            module_list.append(x.replace(os.sep, '.')[3:])


module_list.sort()

for m in module_list:
    if VERBOSE:
        print("Importing", m)
        print('Import Spec', importlib.util.find_spec(m))
    try:
        importlib.import_module(m)
    except ImportError:
        print("ERROR: could not import", m)

# Search all mpf modules
# l = [(x, sys.modules[x],
#       os.path.basename(sys.modules[x].__file__).rsplit('.', 1)[0])
#       for x in sys.modules if x.startswith('mpf') and sys.modules[x]]

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


# Extract packages from modules
packages = []  # high level packages (e.g. folders)
modules = {}  # individual modules
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

# Create index
api_index = '''MPF API Reference
-----------------

Here's everything that's in the MPF package. Note there are separate indexes
for MPF-MC.

.. toctree::
   :maxdepth: 1

'''
api_modules.sort()
for package in api_modules:
    api_index += "   %s.rst\n" % package

writefile('index.rst', api_index)


api_contents = '''API Reference
-------------

.. toctree::
   :maxdepth: 1
   :titlesonly:

'''
api_modules.sort()
for package in packages:
    api_contents += "   %s </mpf/%s.rst>\n" % (package, package)

writefile('../contents.rst', api_contents)


# Create index for all packages
# Note on displaying inherited members;
#     Adding the directive ':inherited-members:' to automodule achieves this
#     but is not always desired. Please see
#         https://github.com/kivy/kivy/pull/3870

template = '\n'.join((
    '=' * 100,
    '$SUMMARY',
    '=' * 100,
    '''
$EXAMPLES_REF

.. automodule:: $PACKAGE
   :members:
   :show-inheritance:
   :undoc-members:
   :inherited-members:

.. toctree::
   :maxdepth: 1
   :titlesonly:

$EXAMPLES
'''))


template_examples = '''.. _example-reference%d:

Examples
--------

%s
'''

template_examples_ref = ('# :ref:`Jump directly to Examples'
                         ' <example-reference%d>`')


def extract_summary_line(doc):
    """
    :param doc: the __doc__ field of a module
    :return: a doc string suitable for a header or empty string
    """
    if doc is None:
        return ''
    for line in doc.split('\n'):
        line = line.strip()
        # don't take empty line
        if len(line) < 1:
            continue
        # ref mark
        if line.startswith('.. _'):
            continue
        return line

for package in packages:
    summary = extract_summary_line(sys.modules[package].__doc__)
    if summary is None or summary == '':
        summary = 'NO SUMMARY (package %s)' % package
    t = template.replace('$SUMMARY', summary)
    t = t.replace('$PACKAGE', package)
    t = t.replace('$EXAMPLES_REF', '')
    t = t.replace('$EXAMPLES', '')

    # search packages
    for subpackage in packages:
        packagemodule = subpackage.rsplit('.', 1)[0]
        if packagemodule != package or len(subpackage.split('.')) <= 2:
            continue
        t += "   %s </mpf/%s.rst>\n" % (subpackage, subpackage)

    # search modules
    m = list(modules.keys())
    m.sort(key=lambda x: extract_summary_line(sys.modules[x].__doc__))
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
    summary = extract_summary_line(sys.modules[module].__doc__)
    if summary is None or summary == '':
        summary = 'NO SUMMARY (module %s)' % package

    # # search examples
    # example_output = []
    # example_prefix = module
    # if module.startswith('mpf.'):
    #     example_prefix = module[5:]
    # example_prefix = example_prefix.replace('.', '_')
    #
    # # try to found any example in framework directory
    # list_examples = glob('%s*.py' % os.path.join(
    #     examples_framework_dir, example_prefix))
    # for x in list_examples:
    #     # extract filename without directory
    #     xb = os.path.basename(x)
    #
    #     # add a section !
    #     example_output.append('File :download:`%s <%s>` ::' % (
    #         xb, os.path.join('..', x)))
    #
    #     # put the file in
    #     with open(x, 'r') as fd:
    #         d = fd.read().strip()
    #         d = '\t' + '\n\t'.join(d.split('\n'))
    #         example_output.append(d)

    t = template.replace('$SUMMARY', summary)
    t = t.replace('$PACKAGE', module)
    # if len(example_output):
    #     refid += 1
    #     example_output = template_examples % (
    #             refid, '\n\n\n'.join(example_output))
    #     t = t.replace('$EXAMPLES_REF', template_examples_ref % refid)
    #     t = t.replace('$EXAMPLES', example_output)
    # else:
    #     t = t.replace('$EXAMPLES_REF', '')
    #     t = t.replace('$EXAMPLES', '')

    t = t.replace('$EXAMPLES_REF', '')
    t = t.replace('$EXAMPLES', '')


    writefile('%s.rst' % module, t)


# Generation finished
print('Auto-generation finished')
