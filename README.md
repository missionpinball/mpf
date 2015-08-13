Dev Branch Notes for 0.20.0-dev3
================================

We have implemented the "machine-wide" modes feature. Here are the changes you
will need to make for your own machines to run.

If you have custom mode code:
* Change 'from mpf.system.modes import Mode' to 'from mpf.system.mode import Mode'
* If you have a mode_start() method, change 'def mode_start(self)' to 'def mode_start(self, \*\*kwargs)'
* If you have a mode_stop() method, change 'def mode_start(self)' to 'def mode_stop(self, \*\*kwargs)'

Mission Pinball Framework (mpf)
===============================

The Mission Pinball Framework (MPF) is a Python-based framework for running real
pinball machines. More information is available at
http://missionpinball.com/framework.

Full documentation (available online or via a PDF) is available at
http://missionpinball.com/docs.

A Sphinx-based API reference is available in the /docs/generated/html
directory of this project. (This is the API reference only. The full
documentation is available via those other web links.)

The Mission Pinball Framework is released via The MIT License. See LICENSE.md
for details.

The Mission Pinball Framework is created by Brian Madden and Gabe Knuth.
