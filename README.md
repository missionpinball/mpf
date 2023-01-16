Mission Pinball Framework (MPF)
===============================

<img align="center" height="146" src="https://missionpinball.org/images/mpf-logo-full.png"/>

<em>...Let's build a pinball machine!</em>

What is Mission Pinball Framework?
----------------------------------

Mission Pinball Framework (MPF) is an open source, cross-platform software for powering real pinball
machines in restaurants, bars, arcades, and elsewhere. MPF is a community-developed project released under the MIT license. It's supported by volunteers in their spare time. Individual pinball hardware makers are responsible for their own platform interface maintenance and contributions.

[![Coverage Status](https://coveralls.io/repos/missionpinball/mpf/badge.svg?branch=dev&service=github)](https://coveralls.io/github/missionpinball/mpf?branch=dev)
[![Test Status](https://github.com/missionpinball/mpf/actions/workflows/run_tests.yml/badge.svg)](https://github.com/missionpinball/mpf/actions/workflows/run_tests.yml)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/1687/badge)](https://bestpractices.coreinfrastructure.org/projects/1687)

Technology and Compatibility
----------------------------

You can use MPF as the software to run a custom-built machine, or (with appropriate interface hardware) existing Williams, Bally, Stern, or Data East pinball machines. MPF interfaces with machines via modern pinball controller hardware, including:

* FAST Pinball controllers
* CobraPin
* Stern SPIKE / SPIKE 2
* Multimorphic P-ROC or P3-ROC
* Open Pinball Project (OPP) open source hardware
* LISY Platform
* Penny K Arcade PKONE
* Arduino Pinball Controller
* Plus many more systems & devices!

MPF is written in Python. It can be run on Windows, Mac, Linux, and Raspberry Pi host machines using the same code and configurations.

Visit the MPF project homepage at https://missionpinball.org. Additional related projects exist as part of the MPF ecosystem, including the "MPF Monitor" which is a graphical application that lets you simulate pinball hardware, and "MPF-MC" which is a media controller which provides graphics and sounds for pinball machines.

Documentation
-------------

* User Docs (installation, tutorials, & reference): https://docs.missionpinball.org
* Developer documentation: https://developer.missionpinball.org/

Support
-------

MPF is open source and has no official support. Some MPF users follow the MPF-users Google group: https://groups.google.com/forum/#!forum/mpf-users. Individual hardware providers may provide additional support for users of their hardware.

Contributing
------------

MPF is a passion project created and maintained by volunteers. If you're a Python coder, documentation writer, or pinball maker, feel free to make a change and submit a pull request. For more information about contributing see the [Contributing Code](http://docs.missionpinball.org/en/latest/about/contributing_to_mpf.html)
and [Contributing Documentation](http://docs.missionpinball.org/en/latest/about/contributing_to_mpf_docs.html) pages.

License
-------

MPF and related projects are released under the MIT License. Refer to the LICENSE file for details. Docs are released under Creative Commons CC BY 4.0.
