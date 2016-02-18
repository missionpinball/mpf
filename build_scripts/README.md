Build Scripts for MPF
=====================

The build_scripts folder contains scripts for building MPF (and testing those builds.) Note that
users of MPF do *not* need to worry about any of this. These scripts are for people developing MPF
who use them to actually build the MPF Python Wheels.

Description of Files in this Folder
===================================

windows-build.bat
-----------------
Batch file you can run on a fresh Windows machine (x86 or x64) with only Python 3.4 and git installed
and nothing else. This script clones the mpf repo (currently harded with a source of z:/git/mpf),
installs mpf from the repo, runs the unit tests, and then builds the wheel. The wheel is then copied
to the "wheels" folder under the directory the script is being run from.

Note that MPF does not currently contain any compiled components, so the generated wheel file is a
"Pure Python Wheel". This means the wheel works for any platform (Windows, Mac, or Linux), though it
is set to require Python 3.4.

windows-test-wheel.bat
----------------------
Batch file which tests the installation of the mpf wheel on a fresh Windows machine. The only
prerequisite is that Python 3.4 is installed. (In fact it's recommended that mothing else is
installed so that the test environment most accruately reflects what an actual end user would
experience when installing MPF.)

This script looks for a folder called "wheels" and then installs MPF from a .whl file there. (If there
are multiple files, it will pick the one with the highest MPF version number.) After that, the script
runs the unit tests.

If the unit tests pass, we can assume we have a good wheel which can be uploaded to PyPI.
