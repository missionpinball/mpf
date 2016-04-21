Building & Deploying MPF
========================

This guide is written for the developers of MPF. It explains how MPF is built
and deployed to PyPI, including how the documentation is built. It's not meant
for end users of MPF (though of course feel free to read it if you're curious).
Really it exists in case Brian gets hit by a bus so the other devs will know how
things work. :)

How the builds work
-------------------

MPF does not contain any binary files that need to be compiled. New versions are
automatically built and deployed to PyPI.

### mpf ###

Commits to mpf are sent to AppVeyor, Travis, Landscape, and Coveralls.

* AppVeyor does 4 builds, Windows x86/x64 and Pythong 3.4/3.5. Unittests are run
on all four. Wheels and gz.tar files are and uploaded to PyPI via twine.
Currently MPF does not contain any compiled components, meaning that the tars
and wheels of all four builds are identical. The twine upload to PyPI process
recognizes if the version that was just built (via the version in ._version)
is already in PyPI, and it won't try to upload it again if so. This essentially
means that the first build of a new version will update PyPI, and subsequent
builds are ignored. It also means that incrementing the version number in
_version.py automatically triggers an update to PyPI.

* Travis builds for Python 3.4 on Linux and runs unit tests. It also runs
coveralls on a successful test. We should add Python 3.5 as well as OS X to the
travis config.

* Landscape is used for code quality checks. It's triggered directly from
commits to GitHub.

* Coveralls checks test coverage. It's triggered from a successful test run on
Travis.


### mpf-mc ###

MPF-MC contains compiled code (currently just the audio library), so it must be
compiled to be used. The CI servers build and compile it for Win x86, x64, and
OS X, and upload platform wheels to PyPI. Linux is built when MPF-MC is
installed by the end user.

MPF-MC also uses AppVeyor, Travis, Landscape, and Coveralls.

* AppVeyor builds Win x86 and Win x64 with Python 3.4. (Python 3.5 is not
supported by Kivy on Windows at this time.) AppVeyor clones mpf from GitHub
(it uses the same branch name as the branch of mpf-mc that's building). This is
done (rather than letting the mpf-mc install get mpf automatically) because we
often update mpf and mpf-mc at the same time, so if mpf-mc builds on AppVeyor
before mpf has been deployed to PyPI, the mpf-mc build could fail because PyPI
doesn't have the latest version of mpf that mpf-mc needs. AppVeyor uses twine to
upload built wheels and a gz.tar to PyPI, again a version change to mpfmc
._version will trigger a new upload to PyPI. Note that unittests are not run
because I don't know how to configure windows to use a virtual display since the
AppVeyor build servers are headless.

* Travis builds Python 3.4 and 3.5 for Linux, and Python 3.5 on OSX. Unittests
are run on Linux only (again because I can't figure out how to do GUI-based
tests on OS X.) Linux runs coveralls after successful unittests. OS X builds
a wheel and uploads it to PyPI. (Linux does not upload anything to PyPI since
AppVeyor uploads the tarball.)

* Coveralls is triggered by a successful test run on the Travis Linux build.

* Landscape is run, triggered by commits to GitHub directly.

### mpf-docs ###

This package contains the source for MPF's user documentation (inluding mpf-mc,
mpf-examples, etc.) New commits automatically build new docs and deploy them
to docs.missionpinball.com. Most of this documentation is hand-written in .rst
files in the repo.

The mpf-docs repo has multiple branches for each version of MPF, e.g. "0.30",
"0.31", etc.

There are two automated helper scripts in the /_doc_tools folder which are
manually run locally from time-to-time:

* build_config_reference_docs.py scans through the config_validator and uses it
to build / update all the .rst file in the /config folder (the configuration
file reference). Basically it's used to make sure that we have everything in the
config file reference. It will create new pages for entries that don't exist,
and it will update the settings lists in current pages to add missing settings
(for new settings that are added) and it will add deprecation warnings to
settings that are no longer found. It's ability to update existing pages is
hit-or-miss, so run this with a clean branch and then look for changed files.
You'll probably have to hand-tweak some things, but at least you'll know that
you go everything.

* build_events_reference_docs.py is used to build the Events reference pages
(a list of every event that MPF or MPF-MC emits) which are contained in the
events folder. These pages are automatically built based on the events
docstrings in the source code. These pages do not need to be manually tweaked--
any changes should be made in the docstrings directly. It appears to work
perfectly, and soon we'll remove the .rst pages from that folder and add the
script to AppVeyor so they're done every time.

The docs are built by AppVeyor. AppVeyor installs sphinx and its related
components, runs the builds, and then FTPs the built docs to
docs.missionpinball.com.

The docs are automatically deployed to a subfolder on the website with a name
that matches the branch version. So *index.rst* in the root of mpf-docs in the
*0.30* branch is deployed to docs.missionpinball.com/0.30/index.html, etc.

The HTML templates are in the /_templates folder, and the navbar in there
contains the top navigation bar with drop-down links to other versions of MPF
documentation. This means that when a new version of MPF is released, the nav
bar of all branches of mpf-docs should be updated to add the latest version to
its list.) This could be automated in the future by using a Python script which
enumerates all the branches from mpf-docs.

### mpf-apidocs ###

This repo contains (or builds) the content for api.missionpinball.com. Similar
to mpf-docs, there's a separate branch for each version of MPF, and the docs
for each version are automatically deployed to that version's subfolder on the
site.

A script called autobuild.py in the root is run first and crawls the folder
structure of the mpf and mpf-mc sources to build out the starting .rst files
which are then processed by sphinx. This script replaces what's tpyically
handled by sphinx-apidoc, since we want more control over how the docs are
built and we have multiple projects we're bringing together in a single docs
package.

Currently these builds are triggered manually. We could automate with webhooks,
but we need to write a script that parses the _version.py file of whichever repo
was just changes to know which folder to deploy it to.

The AppVeyor script installs sphinx and its related components, then clones the
mpf and mpf-mc repos. It also installs mpf-mc (and therefore mpf) from PyPI.
The reason we have two of each repo is because the sphinx needs to crawl the
source (and we want the original source, not the installed versions), but in
doing so, sphinx imports everything, meaning we need Kivy, etc. installed for
that to work. So it's easiest to install mpf-mc from PyPI to get Kivy installed,
but then to clone the repos we want to crawl.

Once the sphinx build is complete, AppVeyor uses a deployment environment to FTP
the files to api.missionpinball.com in a subfolder that matches the branch of
mpf-apidocs.


Checklist for releasing a new version to master
-----------------------------------------------

Here's a list of everything that needs to be done to each repo to release a dev
version to a final version.

### mpf ###

1. Change the version number in dev's mpf._version to remove the "devXXX"
from the version.
1. Merge the latest dev branch into master.
1. Commit and make sure it builds properly and PyPI gets updated.
1. Create a new release on GitHub.
1. Back in the dev branch, change the version number in mpf._version to be the
next version, plus ".dev0.
1. Change the short version in mpf._version to the next version number.
1. Commit

### mpf-mc ###

This is essentialyl the same process as mpf.

1. Change the version number in dev's mpfmc._version to remove the "devXXX"
from the version.
1. Change the mpv version required in mpfmc._version to be the release MPF
version.
1. Merge the latest dev branch into master.
1. Commit and make sure it builds properly and PyPI gets updated.
1. Create a new release on GitHub.
1. Back in the dev branch, change the version number in mpf._version to be the
next version, plus ".dev0.
1. Change the short version in mpfmc._version to the next version number.
1. Commit

### mpf-examples ###

Todo. Need to make sure the examples branch structure matches the mpf/mpf-mc
branch structure.

### mpf-docs ###

1. Fork the latest branch (that you're releasing) and create a new branch for
   the next version.
1. Change the version and release numbers in the new branch's conf.py. (We
could probably change these versions to be automatically pulled in at build
time.)
1. Edit appveyor.yml in the current branch (not the new one you justed
   forked) to point the git clones to master instead of dev.
1. Edit appveyor.yml in the branch that will now be old to point it to the final
   release of the branch its associated with.
1. Edit /_templates/navbar.html to add the link to the new version.
1. Commit

### mpf-apidocs ###

1. Fork the latest branch (that you're releasing) and create a new branch for
   the next version.
1. Change the version and release numbers in the new branch's conf.py. (We
could probably change these versions to be automatically pulled in at build
time.)
1. Edit appveyor.yml in the current branch (not the new one you justed
   forked) to point the git clones to master instead of dev.
1. Edit appveyor.yml in the branch that will now be old to point it to the final
   release of the branch its associated with.
1. Edit /_templates/navbar.html to add the link to the new version.
1. Commit


