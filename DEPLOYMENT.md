Building & Deploying MPF
========================

This guide is written for the developers of MPF. It explains how MPF is built
and deployed to PyPI, including how the documentation is built. It's not meant
for end users of MPF (though of course feel free to read it if you're curious).
Really it exists in case Brian gets hit by a bus so the other devs will know how
things work. :)

Checklist for releasing a new version to master
-----------------------------------------------


### mpf-apidocs ###

#. Fork the latest branch (that you're releasing) and create a new branch for
   the next version.
#. Edit appveyor.yml in the current branch (not the new one you justed
   forked) to point the git clones to master instead of dev.
#. Edit appveyor.yml in the branch that will now be old to point it to the final
   release of the branch its associated with.

How MPF is built
----------------

MPF does not contain any binary files that need to be compiled, so that's easy.
AppVeyor is used. See appveyor.yml for details.
