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
* ``Cython 0.24.1`` (for Linux * Mac)

The additional packages for Linux & Mac are used because MPF-MC is actually compiled on built on those platforms. For
Windows we have pre-built wheels, so compiling is not necessary.

MPF has the following additional dependencies which are specified in the setup.py file and automatically installed when
MPF is installed.

* ``ruamel.yaml`` >=0.10,<0.11: Used for reading & writing YAML files.
* ``pyserial`` >= 3.2.0: Used for serial communication with several types of hardware
* ``pyserial-asyncio`` >= 0.3: Also used for serial communication
* ``typing`` Used for type-checking & type hinting.

Note that some of these dependencies will install their own dependencies.

The setup.py file also specifies a `console_scripts entry point <http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html#the-console-scripts-entry-point>`_
called ``mpf``. This is what lets the user type ``mpf`` from the command environment to launch MPF.