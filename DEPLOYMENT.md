Building & Deploying MPF
========================

This guide is written for the developers of MPF. It explains how MPF is built
and deployed to PyPI, including how the documentation is built. It's not meant
for end users of MPF (though of course feel free to read it if you're curious).
Really it exists in case Brian gets hit by a bus so the other devs will know how
things work. :)

How MPF is built
----------------

MPF does not contain any binary files that need to be compiled, so that's easy.
AppVeyor is used. See appveyor.yml for details.

How the docs are built
----------------------

The documentation contained within the MPF repo is used published to
api.missionpinball.com. (The user docs at docs.missionpinball.com come from the
mpf-docs repo.)

AppVeyor is also used to build and deploy the API docs.
