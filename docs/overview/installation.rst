How MPF installs itself
=======================

This guide explains what happens when MPF is installed.

MPF contains a ``setup.py`` file in the root of the MPF repository. This is the file that's called by *pip* when MPF is
installed. (You can also install MPF without using pip by running ``python3 setup.py`` from the root folder.)

Dependencies
------------

MPF requires Python 3.4 or newer. In our installation instructions, we also recommend that users install/update the
following Python packages to their latest versions:

* ``pip``
* ``setuptools`` (for Linux & Mac)
* ``Cython 0.24.1`` (for Linux & Mac)

The additional packages for Linux & Mac are used because MPF-MC is actually compiled on built on those platforms. For
Windows we have pre-built wheels, so compiling is not necessary.

MPF has the following additional dependencies which are specified in the setup.py file and automatically installed when
MPF is installed.

* ``ruamel.yaml`` >=0.15: Used for reading & writing YAML files.
* ``pyserial`` >= 3.5.0: Used for serial communication with several types of hardware
* ``pyserial-asyncio`` >= 0.4: Also used for serial communication
* ``sortedcontainers`` >= 2.3.0
* ``asciimatics`` >= 1.12.0
* ``terminaltables`` >= 3.1.0
* ``psutil`` >= 5.7.3
* ``grpcio_tools`` >= 1.34.0
* ``grpcio`` >= 1.34.0
* ``protobuf`` >= 3.14.0
* ``prompt_toolkit`` >= 3.0.8
* ``typing`` Used for type-checking & type hinting. This is built-in to Python versions above 3.5.

Note that some of these dependencies will install their own dependencies.

The setup.py file also specifies a `console_scripts entry point <http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html#the-console-scripts-entry-point>`_
called ``mpf``. This is what lets the user type ``mpf`` from the command environment to launch MPF.

In order to build the developer documentation, you will also need:

* ``sphinx``
* ``sphinx_rtd_theme``
* ``sphinxcontrib.napoleon``
* ``gitpython``

Building the developer documentation requires a symbolic link from ``mpf\docs\examples`` to a checkout of the ``mpf-examples`` repository. 
This is normally automatically created when the documentation is built, but under Windows 10 and higher, symlinks can only be created by 
administrators, so the process will fail. If you would prefer not to run the build as an administrator, you can create the link manually 
by running ``mklink /d examples <examples directory>`` at the command line from inside the ``docs`` directory.

