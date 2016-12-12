Building & Deploying MPF
========================

*Last updated Dec 1, 2016*

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

* AppVeyor does 4 builds, Windows x86/x64 and Python 3.4/3.5. Unittests are run
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
MacOS, and upload platform wheels to PyPI. Linux is built when MPF-MC is
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

* Travis builds for Ubuntu 14.04, Ubuntu 16.04, Debian Jessie, and MacOS.
Unittests are run on Linux only (again because I can't figure out how to do GUI-based
tests on OS X.) Linux runs coveralls after successful unittests. MacOS builds
a wheel and uploads it to PyPI. (Linux does not upload anything to PyPI since
AppVeyor uploads the tarball.)

* Coveralls is triggered by a successful test run on the Travis Linux build.

* Landscape is run, triggered by commits to GitHub directly.

### mpf-docs ###

This package contains the source for MPF's user documentation (including mpf-mc,
mpf-examples, etc.) New commits automatically build new docs and deploy them
to docs.missionpinball.org which is hosted by Read the Docs. Most of this
documentation is hand-written in .rst files in the repo.

The mpf-docs repo has multiple branches for each version of MPF, e.g. "0.30",
"0.31", as well as a "latest" version which is always the most recent version
of the docs.

There are automated helper scripts in the /_doc_tools folder which are
manually run locally from time-to-time:

Checklist for releasing a new version to master
-----------------------------------------------

Here's a list of everything that needs to be done to each repo to release a dev
version to a final version.

### mpf ###

1. Fork dev into a new branch with a name like "0.32.x".
2. Change the version number in mpf._version.py to remove the "devXXX"
   from the version, so it's like "0.32.0"
3. Publish and make sure it builds properly and PyPI gets updated.
4. Delete the old ".devXXX" versions from PyPI
5. Create a new release on GitHub.
6. Back in the dev branch, change the version number in mpf._version to be the
   next version, plus ".dev0.
7. Change the short version in mpf._version to the next version number.
8. Commit

### mpf-mc ###

This is essentially the same process as mpf.

1. Follow the same steps as mpf above
2. Verify on PyPI that Mac, Win x86, and Win x64 wheels are there. Also verify
   that tar.gz is there.


### mpf-examples ###

Todo. Need to make sure the examples branch structure matches the mpf/mpf-mc
branch structure.

### mpf-docs ###

1. The branch called "latest" doesn't have to be forked until there is a
   config_version change since we note versionadded, versionchanged, and
   deprecated directives, meaning the latest branch is good for several
   versions of MPF.

2. When you do a config_version change, fork "latest" into a new branch
   with a name that includes the range of old versions. For example,
   "0.30-0.32".


