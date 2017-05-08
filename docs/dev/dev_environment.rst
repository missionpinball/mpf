Setting up your dev environment
===============================

If you want to work on the core MPF or MPF-MC code, you have to install MPF and
MPF-MC a bit differently than the normal process.

Why? Because normally when you install MPF and MPF-MC via *pip*, they get
installed as Python packages into your ``Python/Lib/site-packages`` folder, and
that location is not too conducive to editing MPF source code since it's in a
deep random location.

1. Install a git client
-----------------------

2. Clone the MPF and/or MPF-MC repo(s)
--------------------------------------

Clone the mpf repository and its submodules :

::

    git clone --recursive https://github.com/missionpinball/mpf.git


Same thing for the mpf-mc repository :

::

    git clone --recursive https://github.com/missionpinball/mpf-mc.git



3. Install MPF / MPF-MC in "developer" mode
-------------------------------------------

Create a "virtualenv" for your MPF development in a mpf-env directory (Note : if you don't have virtualenv installed, you can get it through pip : pip3 install virtualenv) :

::

    virtualenv -p python3 mpf-venv

Enter the newly created virtualenv :

::

    source mpf-venv/bin/activate


Each time you'll work with your MPF development version you'll have to switch to this environment.  Note: in this environment, thanks to the "-p python3" option of virtualenv, the version of python and pip is 3.X .

Install mpf and mpf-mc in this environment :

::

    pip install -e mpf
    pip install -e mpf-mc

You should now be done, give a try with

::

    mpf --version


Note : you could also install mpf and mpf-mc in your global environment using "sudo pip3 install -e mpf" and "sudo pip3 install -e mpf-mc" or in your user environment using : "pip3 install --user -e mpf" and "pip3 install --user -e mpf-mc"


4. Make your changes
--------------------

Be sure to add your name to the AUTHORS file in the root of the MPF or MPF-MC
repo!

5. Submit a pull request
------------------------
If your change fixes an open issue, reference that issue number in the comments,
like "fixes #123".
