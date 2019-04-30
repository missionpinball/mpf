Setting up your MPF Dev Environment
===================================

If you want to work on the core MPF or MPF-MC code, you have to install MPF and
MPF-MC a bit differently than the normal process.

Why? Because normally when you install MPF and MPF-MC via *pip*, they get
installed as Python packages into your ``Python/Lib/site-packages`` folder, and
that location is not too conducive to editing MPF source code since it's in a
deep random location. Also, if you ever ran *pip* again to update your MPF installation,
you would potentially overwrite any changes you made.

Instead, you need to install MPF and MPF-MC in "developer" (also known as "editable") mode.
This mode will let you run MPF and MPF-MC from the folder of your choice, and will allow
code changes or additions you make to be immediately available whenever you run MPF.

1. Install a git client
-----------------------

MPF is cross-platform and runs the same on Mac, Windows, or Linux. So any changes or
additions you make should work on all platforms.

If you're on Windows or Mac, the easiest way to get a git client installed is to use
the `GitHub Desktop app <https://desktop.github.com/>`_. This app will also install the
git command line tools.

2. Clone the MPF and/or MPF-MC repo(s)
--------------------------------------

Clone the mpf repository and its submodules :

::

    git clone --recursive https://github.com/missionpinball/mpf.git


Same thing for the mpf-mc repository :

::

    git clone --recursive https://github.com/missionpinball/mpf-mc.git

If you're using the GitHub Desktop app, you can also browse to the repos on GitHub
and click the green "Clone or Download" button, and then click the "Open in Desktop"
link. That will pop up a box that prompts you to pick a folder for the local codebase.

Then inside that folder, you'll end up with an ``mpf`` folder for MPF and ``mpf-mc``
folder for MPF-MC.

3. Install MPF / MPF-MC in "developer" mode
-------------------------------------------

Create a "virtualenv" for your MPF development in a mpf-env directory (Note : if you don't have
virtualenv installed, you can get it via pip by running ``pip3 install virtualenv``.

Using virtualenv lets you keep all the other Python packages MPF needs (pyserial, pyyaml,
kivy, etc.) together in a "virtual" environment that you'll use for MPF and helps keep
everything in your Python environment cleaner in general.

Create a new virtualenv called "mpf-venv" (or whatever you want to name it) like this:

::

    virtualenv -p python3 mpf-venv

Then enter the newly-created virtualenv:

::

    source mpf-venv/bin/activate

On Macs, you will need to uninstall and reinstall kivy in the the virtual envirment to avoid ambiguous kivy library errors.

::

    1) pip uninstall kivy
    2) pip install kivy -no-binary :all:

Each time you'll work with your MPF development version you'll have to switch to this environment.

::

    source mpf-venv/bin/activate

Note: in this environment, thanks to the "-p python3" option of virtualenv, the version of Python and
pip is 3.x automatically.

Next you'll install MPF and MPF-MC. This is pretty much like a regular install, except
that you'll also use the ``-e`` command line option which means these packages will
be installed in "editable" mode.

Install mpf and mpf-mc like this:

::

    pip install -e mpf
    pip install -e mpf-mc

You should now be done, and you can verify that everyething is installed properly via:

::

    mpf --version


Note : you could also install mpf and mpf-mc in your global environment using
``sudo pip3 install -e mpf`` and ``sudo pip3 install -e mpf-mc``, or in your user
environment using ``pip3 install --user -e mpf`` and ``pip3 install --user -e mpf-mc``.


4. Make your changes
--------------------

Be sure to add your name to the ``AUTHORS`` file in the root of the MPF or MPF-MC
repo!

5. Write / update unit tests
----------------------------

We make heavy use of unit tests to ensure that future changes don't break existing
functionality. So write new unit tests to cover whatever you just wrote, and be sure
to rerun all the unit tests to make sure your changes or additions didn't break
anything else.

More information on creating and running MPF unit tests is :doc:`here </testing/index>`.

6. Submit a pull request
------------------------
If your change fixes an open issue, reference that issue number in the comments,
like "fixes #123".
