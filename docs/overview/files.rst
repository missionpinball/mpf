MPF Files & Modules
===================

The MPF packages contains the following folders:

* ``/build_scripts``: Scripts which can be used to locally build & test MPF packages and wheels
* ``/docs``: The Sphinx-based developer docs that you're reading now
* ``/mpf``: The actual mpf package that's copied to your machine when MPF is installed
* ``/tools``: A few random tools

The MPF package
---------------

The MPF package (e.g. the ``/mpf`` subfolder which is copied to your install location when you install MPF) contains
the following folders:

* ``/assets``: Contains the asset classes used in MPF (the "shows" asset class)
* ``/commands``: Modules for the command-line interface for MPF
* ``/config_players:`` Modules for the built-in config_players
* ``/core``: Core MPF system modules
* ``/devices``: Device modules
* ``/exceptions``: MPF exception classes
* ``/file_interfaces``: MPF file interfaces (current just YAML, could support more in the future)
* ``/migrator``: MPF Migrator files
* ``/modes``: Code for built-in modes (game, attract, tilt, credits, etc.)
* ``/platforms``: Hardware platform modules
* ``/plugins``: Built-in MPF plugins
* ``/tests``: MPF unit tests

It also includes the following files in the package root:

* ``__init__.py``: Makes the MPF folder a package
* ``__main__.py``: Allows the MPF commands to run
* ``_version.py``: Contains version strings used throughout MPF for the current version
* ``mpfconfig.yaml``: The "base" machine config file that is used for all machines (unless this is specifically
  overridden via the command-line options)